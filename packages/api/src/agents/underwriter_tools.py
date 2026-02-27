# This project was developed with assistance from AI tools.
"""LangGraph tools for the underwriter assistant agent.

These wrap existing services so the underwriter agent can review the
underwriting queue, inspect application details, and (in PR 2) perform
risk assessments and generate preliminary recommendations.

Design note -- session-per-tool-call:
    Each tool opens its own ``SessionLocal()`` context rather than sharing
    a single session across the agent turn.  This is intentional: LangGraph
    tool nodes run as independent async tasks and may execute in any order,
    so sharing a session would risk interleaved flushes, stale reads, and
    MissingGreenlet errors.  The per-tool pattern keeps each DB interaction
    self-contained and avoids cross-tool state leakage.
"""

from typing import Annotated

from db.database import SessionLocal
from db.enums import ApplicationStage, UserRole
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from ..middleware.auth import build_data_scope
from ..schemas.auth import UserContext
from ..services.application import get_application, list_applications
from ..services.audit import write_audit_event
from ..services.condition import get_conditions
from ..services.document import list_documents
from ..services.rate_lock import get_rate_lock_status
from ..services.urgency import compute_urgency


def _user_context_from_state(state: dict) -> UserContext:
    """Build a UserContext from the agent's graph state."""
    user_id = state.get("user_id", "anonymous")
    role_str = state.get("user_role", "underwriter")
    role = UserRole(role_str)
    return UserContext(
        user_id=user_id,
        role=role,
        email=state.get("user_email") or f"{user_id}@summit-cap.local",
        name=state.get("user_name") or user_id,
        data_scope=build_data_scope(role, user_id),
    )


@tool
async def uw_queue_view(
    state: Annotated[dict, InjectedState],
) -> str:
    """View the underwriting queue sorted by urgency.

    Shows all applications currently in the underwriting stage with
    borrower names, loan amounts, assigned LO, days in queue, rate lock
    status, and urgency indicators.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        applications, total = await list_applications(
            session,
            user,
            filter_stage=ApplicationStage.UNDERWRITING,
            limit=50,
        )

        if total == 0:
            await write_audit_event(
                session,
                event_type="data_access",
                user_id=user.user_id,
                user_role=user.role.value,
                event_data={"action": "underwriter_queue_view", "result_count": 0},
            )
            await session.commit()
            return "No applications in underwriting queue."

        urgency_map = await compute_urgency(session, applications)

        await write_audit_event(
            session,
            event_type="data_access",
            user_id=user.user_id,
            user_role=user.role.value,
            event_data={
                "action": "underwriter_queue_view",
                "result_count": total,
            },
        )
        await session.commit()

    # Sort by urgency level (critical first -- lower enum value = higher urgency)
    def sort_key(app):
        indicator = urgency_map.get(app.id)
        return indicator.level.value if indicator else 99

    applications.sort(key=sort_key)

    lines = [f"Underwriting Queue ({total} application{'s' if total != 1 else ''}):", ""]
    for app in applications:
        indicator = urgency_map.get(app.id)
        urgency_label = indicator.level.name if indicator else "NORMAL"
        days = indicator.days_in_stage if indicator else 0

        # Borrower name(s)
        borrower_names = []
        for ab in app.application_borrowers or []:
            if ab.borrower:
                borrower_names.append(f"{ab.borrower.first_name} {ab.borrower.last_name}")
        names = ", ".join(borrower_names) if borrower_names else "Unknown"

        loan_amt = f"${app.loan_amount:,.0f}" if app.loan_amount else "N/A"
        prop = app.property_address or "N/A"
        lo = app.assigned_to or "Unassigned"

        line = (
            f"- App #{app.id}: {names} | {loan_amt} | {prop} | "
            f"LO: {lo} | {days}d in queue | Urgency: {urgency_label}"
        )

        if indicator and indicator.factors:
            line += f" ({', '.join(indicator.factors)})"

        lines.append(line)

    return "\n".join(lines)


@tool
async def uw_application_detail(
    application_id: int,
    state: Annotated[dict, InjectedState],
) -> str:
    """Get a detailed view of a loan application for underwriting review.

    Includes borrower profile, financial summary, loan details, documents
    with quality flags, conditions, and rate lock status.

    Args:
        application_id: The loan application ID to inspect.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        app = await get_application(session, user, application_id)
        if app is None:
            return "Application not found or you don't have access to it."

        # Financials -- separate query (session-per-tool isolation pattern)
        from db import ApplicationFinancials
        from sqlalchemy import select

        fin_stmt = select(ApplicationFinancials).where(
            ApplicationFinancials.application_id == application_id
        )
        fin_result = await session.execute(fin_stmt)
        financials = fin_result.scalars().all()

        documents, doc_total = await list_documents(session, user, application_id, limit=50)
        conditions = await get_conditions(session, user, application_id)
        rate_lock = await get_rate_lock_status(session, user, application_id)

        await write_audit_event(
            session,
            event_type="data_access",
            user_id=user.user_id,
            user_role=user.role.value,
            application_id=application_id,
            event_data={"action": "underwriter_detail_view"},
        )
        await session.commit()

    stage = app.stage.value if app.stage else "inquiry"
    lines = [
        f"Application #{application_id} -- Underwriting Detail",
        f"Stage: {stage.replace('_', ' ').title()}",
        "",
    ]

    # Borrower Profile
    lines.append("BORROWER PROFILE:")
    for ab in app.application_borrowers or []:
        if ab.borrower:
            b = ab.borrower
            role_label = "Primary" if ab.is_primary else "Co-borrower"
            lines.append(f"  {role_label}: {b.first_name} {b.last_name} ({b.email})")
            if b.employment_status:
                emp = (
                    b.employment_status.value
                    if hasattr(b.employment_status, "value")
                    else str(b.employment_status)
                )
                lines.append(f"    Employment: {emp.replace('_', ' ').title()}")

    # Financial Summary
    lines.append("")
    lines.append("FINANCIAL SUMMARY:")
    if financials:
        total_income = sum((f.gross_monthly_income or 0) for f in financials)
        total_debts = sum((f.monthly_debts or 0) for f in financials)
        total_assets = sum((f.total_assets or 0) for f in financials)
        credit_scores = [f.credit_score for f in financials if f.credit_score]
        min_credit = min(credit_scores) if credit_scores else None

        lines.append(f"  Gross monthly income: ${total_income:,.2f}")
        lines.append(f"  Monthly debts: ${total_debts:,.2f}")
        if total_income > 0:
            dti = float(total_debts) / float(total_income) * 100
            lines.append(f"  DTI ratio: {dti:.1f}%")
        lines.append(f"  Total assets: ${total_assets:,.2f}")
        if min_credit is not None:
            lines.append(f"  Lowest credit score: {min_credit}")
    else:
        lines.append("  No financial data on file.")

    # Loan Details
    lines.append("")
    lines.append("LOAN DETAILS:")
    if app.loan_type:
        lines.append(f"  Loan type: {app.loan_type.value}")
    if app.loan_amount:
        lines.append(f"  Loan amount: ${app.loan_amount:,.2f}")
    if app.property_value:
        lines.append(f"  Property value: ${app.property_value:,.2f}")
        if app.loan_amount and app.property_value:
            ltv = float(app.loan_amount) / float(app.property_value) * 100
            lines.append(f"  LTV ratio: {ltv:.1f}%")
    if app.property_address:
        lines.append(f"  Property: {app.property_address}")

    # Documents
    lines.append("")
    if doc_total > 0:
        lines.append(f"DOCUMENTS ({doc_total}):")
        for doc in documents:
            doc_type = doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type)
            status_val = doc.status.value if hasattr(doc.status, "value") else str(doc.status)
            line = f"  - [{doc.id}] {doc_type}: {status_val}"
            if doc.quality_flags:
                line += f" (issues: {doc.quality_flags})"
            lines.append(line)
    else:
        lines.append("DOCUMENTS: None on file.")

    # Conditions
    lines.append("")
    if conditions:
        lines.append(f"CONDITIONS ({len(conditions)}):")
        for c in conditions:
            status_val = c.get("status", "")
            desc = c.get("description", "")
            severity = c.get("severity", "")
            lines.append(f"  - [{status_val}] {desc} ({severity})")
    elif conditions is not None:
        lines.append("CONDITIONS: None.")
    else:
        lines.append("CONDITIONS: Unable to load.")

    # Rate Lock
    lines.append("")
    if rate_lock:
        rl_status = rate_lock.get("status", "none")
        if rl_status == "none":
            lines.append("RATE LOCK: None on file.")
        else:
            lines.append("RATE LOCK:")
            lines.append(f"  Status: {rl_status.title()}")
            if rate_lock.get("locked_rate") is not None:
                lines.append(f"  Rate: {rate_lock['locked_rate']:.3f}%")
            if rate_lock.get("expiration_date"):
                days = rate_lock.get("days_remaining", 0)
                lines.append(
                    f"  Expires: {rate_lock['expiration_date'][:10]} ({days} days remaining)"
                )
            if rate_lock.get("is_urgent"):
                lines.append("  *** URGENT: Rate lock expiring within 7 days ***")
    else:
        lines.append("RATE LOCK: Unable to load.")

    return "\n".join(lines)
