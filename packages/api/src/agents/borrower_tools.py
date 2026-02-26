# This project was developed with assistance from AI tools.
"""LangGraph tools for the borrower assistant agent.

These wrap the completeness and status services so the agent can
check document requirements, application status, and regulatory
deadlines during a conversation.  DB-backed tools use InjectedState
to receive the caller's identity from the graph state.
"""

from datetime import date, datetime, timedelta
from typing import Annotated

from db.database import SessionLocal
from db.enums import UserRole
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from ..middleware.auth import _build_data_scope
from ..schemas.auth import UserContext
from ..services.audit import write_audit_event
from ..services.completeness import check_completeness
from ..services.condition import get_conditions, respond_to_condition
from ..services.disclosure import get_disclosure_status
from ..services.rate_lock import get_rate_lock_status
from ..services.status import get_application_status

# REQ-CC-17 disclaimer appended to all regulatory deadline responses
_REGULATORY_DISCLAIMER = (
    "\n\n*This content is simulated for demonstration purposes "
    "and does not constitute legal or regulatory advice.*"
)


def _user_context_from_state(state: dict) -> UserContext:
    """Build a UserContext from the agent's graph state."""
    user_id = state.get("user_id", "anonymous")
    role_str = state.get("user_role", "borrower")
    role = UserRole(role_str)
    return UserContext(
        user_id=user_id,
        role=role,
        email=f"{user_id}@summit-cap.local",
        name=user_id,
        data_scope=_build_data_scope(role, user_id),
    )


@tool
async def document_completeness(
    application_id: int,
    state: Annotated[dict, InjectedState],
) -> str:
    """Check which documents have been uploaded and which are still needed for a loan application.

    Args:
        application_id: The loan application ID to check.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        result = await check_completeness(session, user, application_id)

    if result is None:
        return "Application not found or you don't have access to it."

    lines = [
        f"Document completeness for application {application_id}:",
        f"Status: {'Complete' if result.is_complete else 'Incomplete'} "
        f"({result.provided_count}/{result.required_count} documents provided)",
        "",
    ]
    for req in result.requirements:
        status = "Provided" if req.is_provided else "MISSING"
        line = f"- {req.label}: {status}"
        if req.quality_flags:
            line += f" (issues: {', '.join(req.quality_flags)})"
        lines.append(line)

    missing = [r for r in result.requirements if not r.is_provided]
    if missing:
        lines.append("")
        lines.append("Next step: Upload " + missing[0].label)

    return "\n".join(lines)


@tool
async def application_status(
    application_id: int,
    state: Annotated[dict, InjectedState],
) -> str:
    """Get the current status summary for a loan application including stage, document progress, and pending actions.

    Args:
        application_id: The loan application ID to check.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        result = await get_application_status(session, user, application_id)

    if result is None:
        return "Application not found or you don't have access to it."

    lines = [
        f"Application {application_id} Status:",
        f"Stage: {result.stage_info.label}",
        f"  {result.stage_info.description}",
        f"  Next step: {result.stage_info.next_step}",
        f"  Typical timeline: {result.stage_info.typical_timeline}",
        "",
        f"Documents: {result.provided_doc_count}/{result.required_doc_count} "
        f"({'complete' if result.is_document_complete else 'incomplete'})",
    ]

    if result.open_condition_count > 0:
        lines.append(f"Open conditions: {result.open_condition_count}")

    if result.pending_actions:
        lines.append("")
        lines.append("Pending actions:")
        for action in result.pending_actions:
            lines.append(f"- {action.description}")

    return "\n".join(lines)


@tool
def regulatory_deadlines(
    application_date: str,
    current_stage: str,
) -> str:
    """Look up regulatory deadlines that may apply to a loan application.

    Args:
        application_date: The date the application was created (YYYY-MM-DD format).
        current_stage: The current application stage (e.g. 'application', 'processing').
    """
    try:
        app_date = datetime.strptime(application_date, "%Y-%m-%d").date()
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD." + _REGULATORY_DISCLAIMER

    today = date.today()
    lines = [f"Regulatory deadlines for application dated {application_date}:"]

    # Pre-application stages don't trigger regulatory clocks
    pre_app_stages = {"inquiry", "prequalification"}
    if current_stage in pre_app_stages:
        lines.append(
            "No regulatory deadlines apply yet. Deadlines begin when "
            "a formal application is submitted."
        )
        return "\n".join(lines) + _REGULATORY_DISCLAIMER

    # Reg B (ECOA): Lender must notify applicant of action taken within
    # 30 calendar days of receiving a completed application.
    reg_b_deadline = app_date + timedelta(days=30)
    reg_b_remaining = (reg_b_deadline - today).days
    if reg_b_remaining > 0:
        lines.append(
            f"- Reg B (ECOA) 30-day notice: Decision or notice of action required by "
            f"{reg_b_deadline.isoformat()} ({reg_b_remaining} days remaining)"
        )
    else:
        lines.append(
            f"- Reg B (ECOA) 30-day notice: Deadline was {reg_b_deadline.isoformat()} "
            f"({abs(reg_b_remaining)} days ago)"
        )

    # TRID: Loan Estimate must be delivered within 3 business days
    # of receiving a completed application.
    trid_deadline = app_date + timedelta(days=3)
    trid_remaining = (trid_deadline - today).days
    if trid_remaining > 0:
        lines.append(
            f"- TRID Loan Estimate: Must be delivered by "
            f"{trid_deadline.isoformat()} ({trid_remaining} days remaining)"
        )
    elif trid_remaining == 0:
        lines.append(f"- TRID Loan Estimate: Due today ({trid_deadline.isoformat()})")
    else:
        lines.append(
            f"- TRID Loan Estimate: Was due by {trid_deadline.isoformat()} "
            f"({abs(trid_remaining)} days ago)"
        )

    return "\n".join(lines) + _REGULATORY_DISCLAIMER


@tool
async def acknowledge_disclosure(
    application_id: int,
    disclosure_id: str,
    borrower_confirmation: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """Record a borrower's acknowledgment of a required disclosure in the audit trail.

    Call this when the borrower confirms they have received and reviewed
    a disclosure (e.g., "yes", "I acknowledge", "I agree").

    Args:
        application_id: The loan application ID.
        disclosure_id: Identifier of the disclosure (loan_estimate, privacy_notice, hmda_notice, equal_opportunity_notice).
        borrower_confirmation: The borrower's exact confirmation text.
    """
    from ..services.disclosure import _DISCLOSURE_BY_ID

    disclosure = _DISCLOSURE_BY_ID.get(disclosure_id)
    if disclosure is None:
        valid = ", ".join(sorted(_DISCLOSURE_BY_ID.keys()))
        return f"Unknown disclosure '{disclosure_id}'. Valid IDs: {valid}"

    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        await write_audit_event(
            session,
            event_type="disclosure_acknowledged",
            user_id=user.user_id,
            user_role=user.role.value,
            application_id=application_id,
            event_data={
                "disclosure_id": disclosure_id,
                "disclosure_label": disclosure["label"],
                "borrower_confirmation": borrower_confirmation,
            },
        )
        await session.commit()

    return f"Recorded: {disclosure['label']} acknowledged for application {application_id}."


@tool
async def disclosure_status(
    application_id: int,
    state: Annotated[dict, InjectedState],
) -> str:
    """Check which required disclosures have been acknowledged and which are still pending for a loan application.

    Args:
        application_id: The loan application ID to check.
    """
    async with SessionLocal() as session:
        result = await get_disclosure_status(session, application_id)

    lines = [f"Disclosure status for application {application_id}:"]

    if result["all_acknowledged"]:
        lines.append("All required disclosures have been acknowledged.")
    else:
        lines.append(
            f"{len(result['acknowledged'])}/{len(result['acknowledged']) + len(result['pending'])} "
            "disclosures acknowledged."
        )

    if result["acknowledged"]:
        lines.append("")
        lines.append("Acknowledged:")
        for d_id in result["acknowledged"]:
            from ..services.disclosure import _DISCLOSURE_BY_ID

            label = _DISCLOSURE_BY_ID.get(d_id, {}).get("label", d_id)
            lines.append(f"  - {label}")

    if result["pending"]:
        lines.append("")
        lines.append("Pending:")
        for d_id in result["pending"]:
            from ..services.disclosure import _DISCLOSURE_BY_ID

            label = _DISCLOSURE_BY_ID.get(d_id, {}).get("label", d_id)
            lines.append(f"  - {label}")

    return "\n".join(lines)


@tool
async def rate_lock_status(
    application_id: int,
    state: Annotated[dict, InjectedState],
) -> str:
    """Check the current rate lock status for a loan application, including locked rate, expiration date, and days remaining.

    Args:
        application_id: The loan application ID to check.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        result = await get_rate_lock_status(session, user, application_id)

    if result is None:
        return "Application not found or you don't have access to it."

    if result["status"] == "none":
        return (
            f"Application {application_id} does not have a rate lock yet. "
            "Would you like me to explain how rate locks work?"
        )

    lines = [f"Rate lock status for application {application_id}:"]

    if result["status"] == "active":
        lines.append("Status: Active")
        lines.append(f"Locked rate: {result['locked_rate']}%")
        lines.append(f"Lock date: {result['lock_date']}")
        lines.append(f"Expiration date: {result['expiration_date']}")
        days = result["days_remaining"]
        lines.append(f"Days remaining: {days}")

        if days == 0:
            lines.append("")
            lines.append("Your rate lock expires today! Contact your loan officer immediately.")
        elif days <= 3:
            lines.append("")
            lines.append(
                f"Urgent: Your rate lock expires in {days} days. "
                "You need to close soon, or you may need to re-lock at a different rate."
            )
        elif days <= 7:
            lines.append("")
            lines.append(
                f"Note: Your rate lock expires in {days} days. "
                "Please work with your loan officer to close on time."
            )
    else:
        lines.append("Status: Expired")
        lines.append(f"Locked rate was: {result['locked_rate']}%")
        lines.append(f"Expired on: {result['expiration_date']}")
        lines.append("")
        lines.append(
            "Your rate lock has expired. You'll need to request a new rate lock. "
            "Contact your loan officer to discuss current rates."
        )

    return "\n".join(lines)


@tool
async def list_conditions(
    application_id: int,
    state: Annotated[dict, InjectedState],
) -> str:
    """List underwriting conditions for a loan application. Shows open and responded conditions that the borrower needs to address.

    Args:
        application_id: The loan application ID to check.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        result = await get_conditions(session, user, application_id, open_only=True)

    if result is None:
        return "Application not found or you don't have access to it."

    if not result:
        return f"Application {application_id} has no pending conditions. You're all set!"

    lines = [f"Open conditions for application {application_id}:"]
    for i, cond in enumerate(result, 1):
        status_label = cond["status"].replace("_", " ").title()
        line = f"{i}. [{status_label}] {cond['description']} (condition #{cond['id']})"
        if cond.get("response_text"):
            line += f"\n   Your response: {cond['response_text']}"
        lines.append(line)

    open_count = sum(1 for c in result if c["status"] == "open")
    if open_count > 0:
        lines.append("")
        lines.append(
            f"You have {open_count} condition(s) that still need a response. "
            "Would you like to address them now?"
        )

    return "\n".join(lines)


@tool
async def respond_to_condition_tool(
    application_id: int,
    condition_id: int,
    response_text: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """Record the borrower's text response to an underwriting condition. Use this when the borrower provides an explanation or answer for a condition.

    Args:
        application_id: The loan application ID.
        condition_id: The condition ID to respond to (from list_conditions output).
        response_text: The borrower's response text.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        result = await respond_to_condition(
            session,
            user,
            application_id,
            condition_id,
            response_text,
        )

    if result is None:
        return "Application or condition not found, or you don't have access."

    return (
        f"Recorded your response for condition #{result['id']}: "
        f'"{result["description"]}". '
        "The underwriter will review your response."
    )
