# This project was developed with assistance from AI tools.
"""LangGraph tools for underwriting decision management.

Wraps decision service functions so the underwriter agent can render
decisions, draft adverse action notices, and generate LE/CD documents.

Design note -- session-per-tool-call:
    Each tool opens its own ``SessionLocal()`` context rather than sharing
    a single session across the agent turn.  See underwriter_tools.py
    for rationale.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Annotated

from db import ApplicationBorrower, AuditEvent, Borrower, Decision
from db.database import SessionLocal
from db.enums import DecisionType, UserRole
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from sqlalchemy import select

from ..middleware.auth import build_data_scope
from ..schemas.auth import UserContext
from ..services.application import get_application
from ..services.audit import write_audit_event
from ..services.condition import get_condition_summary
from ..services.decision import propose_decision, render_decision
from ..services.rate_lock import get_rate_lock_status

logger = logging.getLogger(__name__)


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


async def _compliance_gate(session, application_id: int) -> str | None:
    """Check that a passing compliance check exists for the application.

    Returns an error message string if the gate fails, or None if it passes.
    """
    comp_stmt = (
        select(AuditEvent)
        .where(
            AuditEvent.application_id == application_id,
            AuditEvent.event_type == "compliance_check",
        )
        .order_by(AuditEvent.timestamp.desc())
        .limit(1)
    )
    comp_result = await session.execute(comp_stmt)
    comp_event = comp_result.scalar_one_or_none()

    if comp_event is None:
        return (
            "Run compliance_check before rendering a decision. No compliance "
            f"check found for application #{application_id}."
        )

    if comp_event.event_data and comp_event.event_data.get("status") == "FAIL":
        failed_checks = comp_event.event_data.get("failed_checks", [])
        failed_str = ", ".join(failed_checks) if failed_checks else "one or more checks"
        return (
            f"Cannot approve application #{application_id} -- compliance check "
            f"FAILED ({failed_str}). Resolve compliance issues before approval."
        )

    return None


def _format_proposal(result: dict) -> str:
    """Format a proposal dict into a human-readable preview for the underwriter."""
    dt = result["decision_type"].replace("_", " ").title()
    lines = [
        "PROPOSED DECISION -- awaiting underwriter confirmation",
        "=====================================================",
        f"  Application: #{result['application_id']}",
        f"  Decision: {dt}",
        f"  Rationale: {result['rationale']}",
    ]

    if result.get("new_stage"):
        stage_label = result["new_stage"].replace("_", " ").title()
        lines.append(
            f"  Stage transition: {result['current_stage'].replace('_', ' ').title()}"
            f" -> {stage_label}"
        )

    if result.get("outstanding_conditions", 0) > 0:
        lines.append(f"  Outstanding conditions: {result['outstanding_conditions']}")

    if result.get("ai_recommendation"):
        lines.append(f"  AI recommendation: {result['ai_recommendation']}")
        if result.get("ai_agreement") is True:
            lines.append("  AI agreement: Yes (concurrence)")
        elif result.get("ai_agreement") is False:
            lines.append("  AI agreement: No (OVERRIDE -- provide override_rationale)")
            if result.get("override_rationale"):
                lines.append(f"  Override rationale: {result['override_rationale']}")

    if result.get("denial_reasons"):
        lines.append("  Denial reasons:")
        for i, reason in enumerate(result["denial_reasons"], 1):
            lines.append(f"    {i}. {reason}")

    lines.extend(
        [
            "",
            "This decision has NOT been recorded yet.",
            "Present this proposal to the underwriter and ask them to confirm",
            "before calling this tool again with confirmed=true.",
        ]
    )

    return "\n".join(lines)


def _format_confirmed(result: dict, rationale: str) -> str:
    """Format a confirmed decision dict into output text."""
    dt = result["decision_type"].replace("_", " ").title()
    lines = [
        f"Decision rendered for application #{result['application_id']}:",
        f"  Decision ID: {result.get('id', 'N/A')}",
        f"  Type: {dt}",
        f"  Rationale: {rationale}",
    ]

    if result.get("new_stage"):
        stage_label = result["new_stage"].replace("_", " ").title()
        lines.append(f"  New stage: {stage_label}")

    if result.get("ai_recommendation"):
        lines.append(f"  AI recommendation: {result['ai_recommendation']}")
        if result.get("ai_agreement") is True:
            lines.append("  AI agreement: Yes (concurrence)")
        elif result.get("ai_agreement") is False:
            lines.append("  AI agreement: No (override)")
            if result.get("override_rationale"):
                lines.append(f"  Override rationale: {result['override_rationale']}")

    if result.get("denial_reasons"):
        lines.append("  Denial reasons:")
        for i, reason in enumerate(result["denial_reasons"], 1):
            lines.append(f"    {i}. {reason}")

    return "\n".join(lines)


@tool
async def uw_render_decision(
    application_id: int,
    decision: str,
    rationale: str,
    confirmed: bool = False,
    denial_reasons: list[str] | None = None,
    credit_score_used: int | None = None,
    credit_score_source: str | None = None,
    contributing_factors: str | None = None,
    override_rationale: str | None = None,
    state: Annotated[dict, InjectedState] = None,
) -> str:
    """Render an underwriting decision on a loan application.

    This tool uses a two-phase flow to ensure human confirmation:

    Phase 1 (confirmed=false, the default): Returns a PROPOSAL showing
    what the decision would do (decision type, stage transition, AI
    agreement). No records are created. You MUST present this proposal
    to the underwriter and wait for their explicit confirmation.

    Phase 2 (confirmed=true): After the underwriter confirms, call
    again with confirmed=true and the same parameters to execute
    the decision. This creates the decision record, transitions the
    application stage, and writes audit events.

    IMPORTANT: Never set confirmed=true without first showing the
    proposal to the underwriter and receiving their explicit approval.

    Args:
        application_id: The loan application ID.
        decision: One of "approve", "deny", or "suspend".
        rationale: Explanation for the decision.
        confirmed: Set to true only after the underwriter confirms the proposal.
        denial_reasons: Required for denials. List of specific reasons.
        credit_score_used: Credit score at time of decision (for denials).
        credit_score_source: Credit bureau source (for denials).
        contributing_factors: Factors that contributed to the decision.
        override_rationale: Explanation when overriding AI recommendation.
    """
    user = _user_context_from_state(state)
    decision_lower = decision.strip().lower()

    async with SessionLocal() as session:
        # Compliance gate for approvals (both phases)
        if decision_lower == "approve":
            gate_error = await _compliance_gate(session, application_id)
            if gate_error:
                return gate_error

        if not confirmed:
            # Phase 1: propose only
            result = await propose_decision(
                session,
                user,
                application_id,
                decision_lower,
                rationale,
                denial_reasons=denial_reasons,
                override_rationale=override_rationale,
            )

            if result is None:
                return f"Application #{application_id} not found or you don't have access to it."
            if "error" in result:
                return result["error"]

            return _format_proposal(result)

        # Phase 2: confirmed -- persist the decision
        result = await render_decision(
            session,
            user,
            application_id,
            decision_lower,
            rationale,
            denial_reasons=denial_reasons,
            credit_score_used=credit_score_used,
            credit_score_source=credit_score_source,
            contributing_factors=contributing_factors,
            override_rationale=override_rationale,
        )

    if result is None:
        return f"Application #{application_id} not found or you don't have access to it."
    if "error" in result:
        return result["error"]

    return _format_confirmed(result, rationale)


@tool
async def uw_draft_adverse_action(
    application_id: int,
    decision_id: int | None = None,
    state: Annotated[dict, InjectedState] = None,
) -> str:
    """Draft an adverse action notice for a denied application.

    Generates an ECOA/FCRA-compliant adverse action notice based on the
    denial decision. Includes credit score disclosure if applicable.
    The notice is stored as an audit event for compliance tracking.

    Args:
        application_id: The loan application ID.
        decision_id: Optional decision ID. If omitted, uses the most recent
            DENIED decision for the application.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        app = await get_application(session, user, application_id)
        if app is None:
            return f"Application #{application_id} not found or you don't have access to it."

        if decision_id is not None:
            # Fetch specific decision
            dec_stmt = select(Decision).where(
                Decision.id == decision_id,
                Decision.application_id == application_id,
            )
        else:
            # Auto-find latest DENIED decision
            dec_stmt = (
                select(Decision)
                .where(
                    Decision.application_id == application_id,
                    Decision.decision_type == DecisionType.DENIED,
                )
                .order_by(Decision.created_at.desc())
                .limit(1)
            )

        dec_result = await session.execute(dec_stmt)
        dec = dec_result.scalar_one_or_none()

        if dec is None:
            if decision_id is not None:
                return f"Decision #{decision_id} not found on application #{application_id}."
            return f"No DENIED decision found on application #{application_id}."

        if dec.decision_type != DecisionType.DENIED:
            return (
                f"Decision #{dec.id} is '{dec.decision_type.value}' -- "
                f"adverse action notices are only for DENIED decisions."
            )

        # Get borrower info
        borrower_name = "Borrower"
        ab_stmt = select(ApplicationBorrower).where(
            ApplicationBorrower.application_id == application_id,
            ApplicationBorrower.is_primary.is_(True),
        )
        ab_result = await session.execute(ab_stmt)
        ab = ab_result.scalar_one_or_none()
        if ab:
            b_stmt = select(Borrower).where(Borrower.id == ab.borrower_id)
            b_result = await session.execute(b_stmt)
            borrower = b_result.scalar_one_or_none()
            if borrower:
                borrower_name = f"{borrower.first_name} {borrower.last_name}"

        # Parse denial reasons
        denial_reasons = []
        if dec.denial_reasons:
            try:
                denial_reasons = json.loads(dec.denial_reasons)
            except (json.JSONDecodeError, TypeError):
                denial_reasons = [dec.denial_reasons]

        # Build notice
        today = datetime.now(UTC).strftime("%B %d, %Y")
        lines = [
            "ADVERSE ACTION NOTICE (SIMULATED)",
            "==================================",
            f"Date: {today}",
            f"Borrower: {borrower_name}",
            f"Application: #{application_id}",
            "",
            "We regret to inform you that your application for a mortgage loan",
            "has been denied for the following reason(s):",
        ]

        if denial_reasons:
            for i, reason in enumerate(denial_reasons, 1):
                lines.append(f"  {i}. {reason}")
        else:
            lines.append("  (No specific reasons recorded)")

        # Credit score disclosure
        if dec.credit_score_used is not None:
            lines.extend(
                [
                    "",
                    "CREDIT SCORE DISCLOSURE:",
                    f"  Your credit score: {dec.credit_score_used}",
                    "  Scores range from 300 to 850.",
                    f"  Source: {dec.credit_score_source or 'Not specified'}",
                ]
            )

        if dec.contributing_factors:
            lines.extend(
                [
                    "",
                    "CONTRIBUTING FACTORS:",
                    f"  {dec.contributing_factors}",
                ]
            )

        lines.extend(
            [
                "",
                "You have the right to:",
                "- Request a copy of the appraisal used in the decision",
                "- Dispute information on your credit report with the credit bureau",
                "- Request the specific reasons for denial within 60 days",
                "- Obtain a free copy of your credit report within 60 days",
                "",
                "Summit Cap Financial | Denver, CO",
                "",
                "DISCLAIMER: This content is simulated for demonstration purposes",
                "and does not constitute an actual adverse action notice.",
            ]
        )

        notice_text = "\n".join(lines)

        # Store as audit event
        await write_audit_event(
            session,
            event_type="adverse_action_notice",
            user_id=user.user_id,
            user_role=user.role.value,
            application_id=application_id,
            event_data={
                "decision_id": decision_id,
                "borrower_name": borrower_name,
                "denial_reasons": denial_reasons,
                "credit_score_used": dec.credit_score_used,
            },
        )
        await session.commit()

    return notice_text


@tool
async def uw_generate_le(
    application_id: int,
    state: Annotated[dict, InjectedState] = None,
) -> str:
    """Generate a simulated Loan Estimate (LE) for an application.

    Creates a simplified Loan Estimate document with key loan terms,
    projected payments, and estimated closing costs. The LE is stored
    as an audit event for compliance tracking.

    Args:
        application_id: The loan application ID.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        app = await get_application(session, user, application_id)
        if app is None:
            return f"Application #{application_id} not found or you don't have access to it."

        # Get borrower info
        borrower_name = "Borrower"
        ab_stmt = select(ApplicationBorrower).where(
            ApplicationBorrower.application_id == application_id,
            ApplicationBorrower.is_primary.is_(True),
        )
        ab_result = await session.execute(ab_stmt)
        ab = ab_result.scalar_one_or_none()
        if ab:
            b_stmt = select(Borrower).where(Borrower.id == ab.borrower_id)
            b_result = await session.execute(b_stmt)
            borrower = b_result.scalar_one_or_none()
            if borrower:
                borrower_name = f"{borrower.first_name} {borrower.last_name}"

        # Get rate lock info
        rate_lock = await get_rate_lock_status(session, user, application_id)

        # Compute simulated values
        loan_amount = float(app.loan_amount) if app.loan_amount else 0
        property_value = float(app.property_value) if app.property_value else 0
        rate = 6.875  # default simulated rate
        if rate_lock and rate_lock.get("locked_rate"):
            rate = float(rate_lock["locked_rate"])

        loan_type = app.loan_type.value if app.loan_type else "conventional_30"
        term_years = 15 if "15" in loan_type else 30
        monthly_rate = rate / 100 / 12
        num_payments = term_years * 12

        if monthly_rate > 0 and loan_amount > 0:
            monthly_payment = (
                loan_amount
                * (monthly_rate * (1 + monthly_rate) ** num_payments)
                / ((1 + monthly_rate) ** num_payments - 1)
            )
        else:
            monthly_payment = 0

        # Simulated closing costs
        origination_fee = loan_amount * 0.01
        appraisal = 550.0
        title_insurance = loan_amount * 0.003
        recording_fees = 150.0
        total_closing = origination_fee + appraisal + title_insurance + recording_fees

        today = datetime.now(UTC).strftime("%B %d, %Y")
        lines = [
            "LOAN ESTIMATE (SIMULATED)",
            "=========================",
            f"Date Issued: {today}",
            f"Borrower: {borrower_name}",
            f"Application: #{application_id}",
            f"Property: {app.property_address or 'N/A'}",
            "",
            "LOAN TERMS:",
            f"  Loan Amount: ${loan_amount:,.2f}",
            f"  Interest Rate: {rate:.3f}%",
            f"  Loan Type: {loan_type.replace('_', ' ').title()}",
            f"  Term: {term_years} years ({num_payments} payments)",
            f"  Monthly P&I: ${monthly_payment:,.2f}",
            "",
            "PROJECTED PAYMENTS:",
            f"  Principal & Interest: ${monthly_payment:,.2f}/month",
            "  Estimated taxes & insurance: Varies by location",
            "",
            "ESTIMATED CLOSING COSTS:",
            f"  Origination fee (1%): ${origination_fee:,.2f}",
            f"  Appraisal: ${appraisal:,.2f}",
            f"  Title insurance: ${title_insurance:,.2f}",
            f"  Recording fees: ${recording_fees:,.2f}",
            f"  Total estimated: ${total_closing:,.2f}",
        ]

        if property_value > 0:
            down_payment = property_value - loan_amount
            ltv = loan_amount / property_value * 100
            lines.extend(
                [
                    "",
                    "CASH TO CLOSE:",
                    f"  Property Value: ${property_value:,.2f}",
                    f"  Down Payment: ${down_payment:,.2f}",
                    f"  Estimated Closing Costs: ${total_closing:,.2f}",
                    f"  Total Cash to Close: ${down_payment + total_closing:,.2f}",
                    f"  LTV: {ltv:.1f}%",
                ]
            )

        lines.extend(
            [
                "",
                "DISCLAIMER: This Loan Estimate is simulated for demonstration",
                "purposes and does not constitute an actual TRID Loan Estimate.",
            ]
        )

        # Update LE delivery date
        app.le_delivery_date = datetime.now(UTC)

        await write_audit_event(
            session,
            event_type="le_generated",
            user_id=user.user_id,
            user_role=user.role.value,
            application_id=application_id,
            event_data={
                "loan_amount": loan_amount,
                "rate": rate,
                "term_years": term_years,
                "monthly_payment": round(monthly_payment, 2),
                "total_closing_costs": round(total_closing, 2),
            },
        )
        await session.commit()

    return "\n".join(lines)


@tool
async def uw_generate_cd(
    application_id: int,
    state: Annotated[dict, InjectedState] = None,
) -> str:
    """Generate a simulated Closing Disclosure (CD) for an application.

    Creates a simplified Closing Disclosure with final loan terms,
    actual closing costs, and cash to close. All conditions must be
    cleared or waived before a CD can be generated.

    Args:
        application_id: The loan application ID.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        app = await get_application(session, user, application_id)
        if app is None:
            return f"Application #{application_id} not found or you don't have access to it."

        # Condition gate: all conditions must be cleared/waived
        cond_summary = await get_condition_summary(session, user, application_id)
        if cond_summary and cond_summary["total"] > 0:
            outstanding = (
                cond_summary["counts"].get("open", 0)
                + cond_summary["counts"].get("responded", 0)
                + cond_summary["counts"].get("under_review", 0)
                + cond_summary["counts"].get("escalated", 0)
            )
            if outstanding > 0:
                return (
                    f"Cannot generate Closing Disclosure for application #{application_id} "
                    f"-- {outstanding} condition(s) still outstanding. Clear or waive all "
                    f"conditions before generating the CD."
                )

        # Get borrower info
        borrower_name = "Borrower"
        ab_stmt = select(ApplicationBorrower).where(
            ApplicationBorrower.application_id == application_id,
            ApplicationBorrower.is_primary.is_(True),
        )
        ab_result = await session.execute(ab_stmt)
        ab = ab_result.scalar_one_or_none()
        if ab:
            b_stmt = select(Borrower).where(Borrower.id == ab.borrower_id)
            b_result = await session.execute(b_stmt)
            borrower = b_result.scalar_one_or_none()
            if borrower:
                borrower_name = f"{borrower.first_name} {borrower.last_name}"

        # Get rate lock info
        rate_lock = await get_rate_lock_status(session, user, application_id)

        # Compute values
        loan_amount = float(app.loan_amount) if app.loan_amount else 0
        property_value = float(app.property_value) if app.property_value else 0
        rate = 6.875
        if rate_lock and rate_lock.get("locked_rate"):
            rate = float(rate_lock["locked_rate"])

        loan_type = app.loan_type.value if app.loan_type else "conventional_30"
        term_years = 15 if "15" in loan_type else 30
        monthly_rate = rate / 100 / 12
        num_payments = term_years * 12

        if monthly_rate > 0 and loan_amount > 0:
            monthly_payment = (
                loan_amount
                * (monthly_rate * (1 + monthly_rate) ** num_payments)
                / ((1 + monthly_rate) ** num_payments - 1)
            )
        else:
            monthly_payment = 0

        # Final closing costs (slightly different from LE for realism)
        origination_fee = loan_amount * 0.01
        appraisal = 550.0
        title_insurance = loan_amount * 0.003
        recording_fees = 175.0
        transfer_tax = property_value * 0.001 if property_value else 0
        total_closing = (
            origination_fee + appraisal + title_insurance + recording_fees + transfer_tax
        )

        today = datetime.now(UTC).strftime("%B %d, %Y")
        closing_date = (datetime.now(UTC)).strftime("%B %d, %Y")

        lines = [
            "CLOSING DISCLOSURE (SIMULATED)",
            "==============================",
            f"Date Issued: {today}",
            f"Closing Date: {closing_date}",
            f"Borrower: {borrower_name}",
            f"Application: #{application_id}",
            f"Property: {app.property_address or 'N/A'}",
            "",
            "LOAN TERMS:",
            f"  Loan Amount: ${loan_amount:,.2f}",
            f"  Interest Rate: {rate:.3f}%",
            f"  Loan Type: {loan_type.replace('_', ' ').title()}",
            f"  Term: {term_years} years ({num_payments} payments)",
            f"  Monthly P&I: ${monthly_payment:,.2f}",
            "",
            "CLOSING COST DETAILS:",
            f"  Origination fee (1%): ${origination_fee:,.2f}",
            f"  Appraisal: ${appraisal:,.2f}",
            f"  Title insurance: ${title_insurance:,.2f}",
            f"  Recording fees: ${recording_fees:,.2f}",
            f"  Transfer tax: ${transfer_tax:,.2f}",
            f"  Total closing costs: ${total_closing:,.2f}",
        ]

        if property_value > 0:
            down_payment = property_value - loan_amount
            lines.extend(
                [
                    "",
                    "CASH TO CLOSE:",
                    f"  Purchase Price: ${property_value:,.2f}",
                    f"  Down Payment: ${down_payment:,.2f}",
                    f"  Total Closing Costs: ${total_closing:,.2f}",
                    f"  Total Cash to Close: ${down_payment + total_closing:,.2f}",
                ]
            )

        lines.extend(
            [
                "",
                "DISCLAIMER: This Closing Disclosure is simulated for demonstration",
                "purposes and does not constitute an actual TRID Closing Disclosure.",
            ]
        )

        # Update CD delivery date
        app.cd_delivery_date = datetime.now(UTC)

        await write_audit_event(
            session,
            event_type="cd_generated",
            user_id=user.user_id,
            user_role=user.role.value,
            application_id=application_id,
            event_data={
                "loan_amount": loan_amount,
                "rate": rate,
                "term_years": term_years,
                "monthly_payment": round(monthly_payment, 2),
                "total_closing_costs": round(total_closing, 2),
            },
        )
        await session.commit()

    return "\n".join(lines)
