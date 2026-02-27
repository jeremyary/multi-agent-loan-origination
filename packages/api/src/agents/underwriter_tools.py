# This project was developed with assistance from AI tools.
"""LangGraph tools for the underwriter assistant agent.

These wrap existing services so the underwriter agent can review the
underwriting queue, inspect application details, perform risk assessments,
and generate preliminary recommendations.

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
from db.enums import ApplicationStage, EmploymentStatus, UserRole
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

        # Sort by urgency level (critical first -- lower enum value = higher urgency)
        def sort_key(a):
            indicator = urgency_map.get(a.id)
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

        # Format output before commit to avoid expired-attribute errors
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
                doc_type = (
                    doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type)
                )
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

        await write_audit_event(
            session,
            event_type="data_access",
            user_id=user.user_id,
            user_role=user.role.value,
            application_id=application_id,
            event_data={"action": "underwriter_detail_view"},
        )
        await session.commit()
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Risk assessment helpers (pure functions)
# ---------------------------------------------------------------------------

_RISK_LOW = "Low"
_RISK_MEDIUM = "Medium"
_RISK_HIGH = "High"


def _compute_risk_factors(app, financials_rows, borrowers) -> dict:
    """Compute risk factors from application data.

    Pure function -- no DB access.  Returns a dict with:
      dti, ltv, credit, income_stability, asset_sufficiency,
      compensating_factors, warnings
    Each factor has: value, rating, notes.
    """
    warnings: list[str] = []

    # --- DTI ---
    total_income = sum(float(f.gross_monthly_income or 0) for f in financials_rows)
    total_debts = sum(float(f.monthly_debts or 0) for f in financials_rows)
    if total_income > 0:
        dti_pct = total_debts / total_income * 100
        if dti_pct < 36:
            dti_rating = _RISK_LOW
        elif dti_pct <= 43:
            dti_rating = _RISK_MEDIUM
        else:
            dti_rating = _RISK_HIGH
        dti = {"value": round(dti_pct, 1), "rating": dti_rating}
    else:
        dti = {"value": None, "rating": None}
        warnings.append("Missing income data -- DTI cannot be computed")

    # --- LTV ---
    loan_amount = float(app.loan_amount or 0)
    property_value = float(app.property_value or 0)
    if property_value > 0 and loan_amount > 0:
        ltv_pct = loan_amount / property_value * 100
        if ltv_pct < 60:
            ltv_rating = _RISK_LOW
        elif ltv_pct <= 80:
            ltv_rating = _RISK_MEDIUM
        else:
            ltv_rating = _RISK_HIGH
        ltv = {"value": round(ltv_pct, 1), "rating": ltv_rating}
    else:
        ltv = {"value": None, "rating": None}
        warnings.append("Missing loan amount or property value -- LTV cannot be computed")

    # --- Credit score ---
    credit_scores = [f.credit_score for f in financials_rows if f.credit_score]
    if credit_scores:
        min_score = min(credit_scores)
        if min_score > 680:
            credit_rating = _RISK_LOW
        elif min_score >= 620:
            credit_rating = _RISK_MEDIUM
        else:
            credit_rating = _RISK_HIGH
        credit = {"value": min_score, "rating": credit_rating}
    else:
        credit = {"value": None, "rating": None}
        warnings.append("No credit score on file")

    # --- Income stability ---
    emp_statuses = []
    for b_info in borrowers:
        emp = b_info.get("employment_status")
        if emp:
            emp_statuses.append(emp)

    if emp_statuses:
        stability_map = {
            EmploymentStatus.W2_EMPLOYEE.value: _RISK_LOW,
            EmploymentStatus.RETIRED.value: _RISK_LOW,
            EmploymentStatus.SELF_EMPLOYED.value: _RISK_MEDIUM,
            EmploymentStatus.OTHER.value: _RISK_MEDIUM,
            EmploymentStatus.UNEMPLOYED.value: _RISK_HIGH,
        }
        ratings = [stability_map.get(e, _RISK_MEDIUM) for e in emp_statuses]
        risk_order = {_RISK_LOW: 0, _RISK_MEDIUM: 1, _RISK_HIGH: 2}
        worst_rating = max(ratings, key=lambda r: risk_order.get(r, 1))
        income_stability = {"value": ", ".join(emp_statuses), "rating": worst_rating}
    else:
        income_stability = {"value": None, "rating": None}
        warnings.append("No employment status on file")

    # --- Asset sufficiency ---
    total_assets = sum(float(f.total_assets or 0) for f in financials_rows)
    if loan_amount > 0 and total_assets > 0:
        asset_ratio = total_assets / loan_amount * 100
        if asset_ratio > 20:
            asset_rating = _RISK_LOW
        elif asset_ratio >= 10:
            asset_rating = _RISK_MEDIUM
        else:
            asset_rating = _RISK_HIGH
        asset_sufficiency = {"value": round(asset_ratio, 1), "rating": asset_rating}
    else:
        asset_sufficiency = {"value": None, "rating": None}
        if total_assets == 0:
            warnings.append("No asset data on file")

    # --- Compensating factors ---
    comp_factors: list[str] = []
    if credit.get("value") and credit["value"] > 740 and dti.get("rating") == _RISK_HIGH:
        comp_factors.append("Strong credit (>740) offsets elevated DTI")
    if ltv.get("value") and ltv["value"] < 60 and credit.get("rating") == _RISK_HIGH:
        comp_factors.append("Low LTV (<60%) offsets weak credit")
    if asset_sufficiency.get("value") and asset_sufficiency["value"] > 50:
        comp_factors.append("High reserves (>50% of loan amount)")

    return {
        "dti": dti,
        "ltv": ltv,
        "credit": credit,
        "income_stability": income_stability,
        "asset_sufficiency": asset_sufficiency,
        "compensating_factors": comp_factors,
        "warnings": warnings,
    }


def _extract_borrower_info(app) -> list[dict]:
    """Extract borrower employment info from an application's borrowers."""
    borrowers = []
    for ab in app.application_borrowers or []:
        if ab.borrower:
            b = ab.borrower
            emp = (
                b.employment_status.value
                if b.employment_status and hasattr(b.employment_status, "value")
                else str(b.employment_status)
                if b.employment_status
                else None
            )
            borrowers.append(
                {
                    "name": f"{b.first_name} {b.last_name}",
                    "is_primary": ab.is_primary,
                    "employment_status": emp,
                }
            )
    return borrowers


@tool
async def uw_risk_assessment(
    application_id: int,
    state: Annotated[dict, InjectedState],
) -> str:
    """Perform a risk assessment on a loan application in underwriting.

    Computes DTI ratio, LTV ratio, credit risk, income stability, and
    asset sufficiency. Identifies compensating factors. This is an advisory
    assessment only -- final decisions require human judgment.

    Args:
        application_id: The loan application ID to assess.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        app = await get_application(session, user, application_id)
        if app is None:
            return "Application not found or you don't have access to it."

        if app.stage != ApplicationStage.UNDERWRITING:
            stage_val = app.stage.value if app.stage else "unknown"
            await write_audit_event(
                session,
                event_type="tool_call",
                user_id=user.user_id,
                user_role=user.role.value,
                application_id=application_id,
                event_data={
                    "tool": "uw_risk_assessment",
                    "error": f"wrong_stage:{stage_val}",
                },
            )
            await session.commit()
            return (
                f"Risk assessment is only available for applications in the UNDERWRITING "
                f"stage. Application #{application_id} is in "
                f"{stage_val.replace('_', ' ').title()}."
            )

        from db import ApplicationFinancials
        from sqlalchemy import select

        fin_stmt = select(ApplicationFinancials).where(
            ApplicationFinancials.application_id == application_id
        )
        fin_result = await session.execute(fin_stmt)
        financials = fin_result.scalars().all()

        borrowers = _extract_borrower_info(app)
        risk = _compute_risk_factors(app, financials, borrowers)

        await write_audit_event(
            session,
            event_type="tool_call",
            user_id=user.user_id,
            user_role=user.role.value,
            application_id=application_id,
            event_data={
                "tool": "uw_risk_assessment",
                "dti": risk["dti"].get("value"),
                "ltv": risk["ltv"].get("value"),
                "credit": risk["credit"].get("value"),
            },
        )
        await session.commit()

    # Format output
    lines = [
        f"Risk Assessment -- Application #{application_id}",
        "",
    ]

    # DTI (Capacity)
    dti = risk["dti"]
    if dti["value"] is not None:
        lines.append(f"CAPACITY (DTI): {dti['value']}% -- {dti['rating']} Risk")
        if dti["value"] < 36:
            lines.append("  Well within conventional guidelines")
        elif dti["value"] <= 43:
            lines.append("  Within QM safe harbor limits")
        else:
            lines.append("  Exceeds QM safe harbor; requires compensating factors or exception")
    else:
        lines.append("CAPACITY (DTI): Incomplete data")

    # LTV (Collateral)
    ltv = risk["ltv"]
    lines.append("")
    if ltv["value"] is not None:
        lines.append(f"COLLATERAL (LTV): {ltv['value']}% -- {ltv['rating']} Risk")
        if ltv["value"] > 80:
            lines.append("  PMI likely required")
    else:
        lines.append("COLLATERAL (LTV): Incomplete data")

    # Credit
    cred = risk["credit"]
    lines.append("")
    if cred["value"] is not None:
        lines.append(f"CREDIT: {cred['value']} (lowest) -- {cred['rating']} Risk")
    else:
        lines.append("CREDIT: No score available")

    # Income stability
    stab = risk["income_stability"]
    lines.append("")
    if stab["value"] is not None:
        lines.append(f"STABILITY: {stab['value']} -- {stab['rating']} Risk")
    else:
        lines.append("STABILITY: No employment data")

    # Asset sufficiency
    assets = risk["asset_sufficiency"]
    lines.append("")
    if assets["value"] is not None:
        lines.append(f"ASSET SUFFICIENCY: {assets['value']}% of loan -- {assets['rating']} Risk")
    else:
        lines.append("ASSET SUFFICIENCY: Incomplete data")

    # Compensating factors
    if risk["compensating_factors"]:
        lines.append("")
        lines.append("COMPENSATING FACTORS:")
        for cf in risk["compensating_factors"]:
            lines.append(f"  + {cf}")

    # Warnings
    if risk["warnings"]:
        lines.append("")
        lines.append("WARNINGS:")
        for w in risk["warnings"]:
            lines.append(f"  ! {w}")

    # Overall risk
    lines.append("")
    ratings = [
        risk["dti"].get("rating"),
        risk["ltv"].get("rating"),
        risk["credit"].get("rating"),
        risk["income_stability"].get("rating"),
        risk["asset_sufficiency"].get("rating"),
    ]
    valid_ratings = [r for r in ratings if r is not None]
    if valid_ratings:
        risk_order = {_RISK_LOW: 0, _RISK_MEDIUM: 1, _RISK_HIGH: 2}
        overall = max(valid_ratings, key=lambda r: risk_order.get(r, 1))
        lines.append(f"OVERALL RISK: {overall}")
    else:
        lines.append("OVERALL RISK: Insufficient data for assessment")

    lines.append("")
    lines.append(
        "DISCLAIMER: This is an advisory assessment only. All regulatory "
        "information is simulated for demonstration purposes."
    )

    return "\n".join(lines)


@tool
async def uw_preliminary_recommendation(
    application_id: int,
    state: Annotated[dict, InjectedState],
) -> str:
    """Generate a preliminary underwriting recommendation for an application.

    Based on risk factors, produces one of: Approve, Approve with Conditions,
    Suspend, or Deny. This is advisory only -- it does NOT create a decision
    record. Final decisions require human underwriter judgment.

    Args:
        application_id: The loan application ID to evaluate.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        app = await get_application(session, user, application_id)
        if app is None:
            return "Application not found or you don't have access to it."

        if app.stage != ApplicationStage.UNDERWRITING:
            stage_val = app.stage.value if app.stage else "unknown"
            await write_audit_event(
                session,
                event_type="tool_call",
                user_id=user.user_id,
                user_role=user.role.value,
                application_id=application_id,
                event_data={
                    "tool": "uw_preliminary_recommendation",
                    "error": f"wrong_stage:{stage_val}",
                },
            )
            await session.commit()
            return (
                f"Preliminary recommendation is only available for applications in the "
                f"UNDERWRITING stage. Application #{application_id} is in "
                f"{stage_val.replace('_', ' ').title()}."
            )

        from db import ApplicationFinancials
        from sqlalchemy import select

        fin_stmt = select(ApplicationFinancials).where(
            ApplicationFinancials.application_id == application_id
        )
        fin_result = await session.execute(fin_stmt)
        financials = fin_result.scalars().all()

        documents, doc_total = await list_documents(session, user, application_id, limit=50)
        borrowers = _extract_borrower_info(app)
        risk = _compute_risk_factors(app, financials, borrowers)

        # Decision tree
        recommendation = "Approve"
        rationale: list[str] = []
        conditions_list: list[str] = []

        dti_val = risk["dti"].get("value")
        ltv_val = risk["ltv"].get("value")
        credit_val = risk["credit"].get("value")

        # --- Deny triggers ---
        deny_reasons: list[str] = []
        if dti_val is not None and dti_val > 55:
            deny_reasons.append(f"DTI ratio ({dti_val}%) exceeds maximum threshold of 55%")
        if credit_val is not None and credit_val < 580:
            deny_reasons.append(f"Credit score ({credit_val}) below minimum threshold of 580")
        if ltv_val is not None and ltv_val > 97:
            deny_reasons.append(f"LTV ratio ({ltv_val}%) exceeds maximum threshold of 97%")

        # Unemployed with no employed co-borrower
        emp_statuses = [b.get("employment_status") for b in borrowers if b.get("employment_status")]
        has_employed = any(
            e in (EmploymentStatus.W2_EMPLOYEE.value, EmploymentStatus.SELF_EMPLOYED.value)
            for e in emp_statuses
        )
        if EmploymentStatus.UNEMPLOYED.value in emp_statuses and not has_employed:
            deny_reasons.append("Primary borrower unemployed with no employed co-borrower")

        if deny_reasons:
            recommendation = "Deny"
            rationale = deny_reasons

        # --- Suspend triggers (only if not denied) ---
        elif not financials:
            recommendation = "Suspend"
            rationale = ["Missing financial data -- cannot complete risk assessment"]
        elif credit_val is None:
            recommendation = "Suspend"
            rationale = ["No credit score on file -- credit pull required"]
        elif doc_total == 0:
            recommendation = "Suspend"
            rationale = ["No documents on file -- cannot verify borrower information"]

        # --- Conditions triggers (only if not denied/suspended) ---
        else:
            if dti_val is not None and 43 < dti_val <= 55:
                conditions_list.append(
                    f"DTI ({dti_val}%) exceeds QM safe harbor -- "
                    "document compensating factors or request exception"
                )
            if ltv_val is not None and ltv_val > 80:
                conditions_list.append(f"LTV ({ltv_val}%) exceeds 80% -- PMI required")
            if credit_val is not None and 580 <= credit_val < 620:
                conditions_list.append(
                    f"Credit score ({credit_val}) below 620 -- "
                    "additional documentation of creditworthiness required"
                )
            if EmploymentStatus.SELF_EMPLOYED.value in emp_statuses:
                conditions_list.append(
                    "Self-employed borrower -- verify 2 years tax returns and business financials"
                )

            if conditions_list:
                recommendation = "Approve with Conditions"
                rationale = [f"{len(conditions_list)} condition(s) must be satisfied"]

        # Audit
        await write_audit_event(
            session,
            event_type="tool_call",
            user_id=user.user_id,
            user_role=user.role.value,
            application_id=application_id,
            event_data={
                "tool": "uw_preliminary_recommendation",
                "recommendation": recommendation,
            },
        )
        await session.commit()

    # Format output
    lines = [
        f"Preliminary Recommendation -- Application #{application_id}",
        "",
        f"RECOMMENDATION: {recommendation}",
        "",
    ]

    if rationale:
        lines.append("RATIONALE:")
        for r in rationale:
            lines.append(f"  - {r}")
        lines.append("")

    if conditions_list:
        lines.append("CONDITIONS:")
        for i, c in enumerate(conditions_list, 1):
            lines.append(f"  {i}. {c}")
        lines.append("")

    if risk["compensating_factors"]:
        lines.append("COMPENSATING FACTORS:")
        for cf in risk["compensating_factors"]:
            lines.append(f"  + {cf}")
        lines.append("")

    lines.append(
        "DISCLAIMER: This is an advisory recommendation only. It does NOT "
        "constitute an official underwriting decision. Final decisions require "
        "human underwriter review and approval. All regulatory information is "
        "simulated for demonstration purposes."
    )

    return "\n".join(lines)
