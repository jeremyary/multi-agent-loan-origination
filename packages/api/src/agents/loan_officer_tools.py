# This project was developed with assistance from AI tools.
"""LangGraph tools for the loan officer assistant agent.

These wrap existing services so the LO agent can review applications,
inspect documents, flag documents for resubmission, check underwriting
readiness, and submit applications to underwriting.

Design note -- session-per-tool-call:
    Each tool opens its own ``SessionLocal()`` context rather than sharing
    a single session across the agent turn.  This is intentional: LangGraph
    tool nodes run as independent async tasks and may execute in any order,
    so sharing a session would risk interleaved flushes, stale reads, and
    MissingGreenlet errors.  The per-tool pattern keeps each DB interaction
    self-contained and avoids cross-tool state leakage.
"""

import json
from typing import Annotated

from db.database import SessionLocal
from db.enums import ApplicationStage, DocumentStatus, UserRole
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from ..middleware.auth import build_data_scope
from ..schemas.auth import UserContext
from ..services.application import get_application, transition_stage
from ..services.audit import write_audit_event
from ..services.completeness import check_completeness, check_underwriting_readiness
from ..services.document import get_document, list_documents, update_document_status
from ..services.status import get_application_status


def _user_context_from_state(state: dict) -> UserContext:
    """Build a UserContext from the agent's graph state."""
    user_id = state.get("user_id", "anonymous")
    role_str = state.get("user_role", "loan_officer")
    role = UserRole(role_str)
    return UserContext(
        user_id=user_id,
        role=role,
        email=state.get("user_email") or f"{user_id}@summit-cap.local",
        name=state.get("user_name") or user_id,
        data_scope=build_data_scope(role, user_id),
    )


@tool
async def lo_application_detail(
    application_id: int,
    state: Annotated[dict, InjectedState],
) -> str:
    """Get a detailed summary of a loan application including borrower info, financials, stage, documents, and conditions.

    Args:
        application_id: The loan application ID to review.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        app = await get_application(session, user, application_id)
        if app is None:
            return "Application not found or you don't have access to it."

        status = await get_application_status(session, user, application_id)

    stage = app.stage.value if app.stage else "inquiry"
    lines = [
        f"Application #{application_id} Summary:",
        f"Stage: {stage.replace('_', ' ').title()}",
    ]

    if app.loan_type:
        lines.append(f"Loan type: {app.loan_type.value}")
    if app.property_address:
        lines.append(f"Property: {app.property_address}")
    if app.loan_amount:
        lines.append(f"Loan amount: ${app.loan_amount:,.2f}")
    if app.property_value:
        lines.append(f"Property value: ${app.property_value:,.2f}")

    # Borrower info
    for ab in app.application_borrowers or []:
        if ab.borrower:
            b = ab.borrower
            role_label = "Primary borrower" if ab.is_primary else "Co-borrower"
            lines.append(f"{role_label}: {b.first_name} {b.last_name} ({b.email})")

    # Status summary
    if status:
        lines.append("")
        lines.append(
            f"Documents: {status.provided_doc_count}/{status.required_doc_count} "
            f"({'complete' if status.is_document_complete else 'incomplete'})"
        )
        if status.open_condition_count > 0:
            lines.append(f"Open conditions: {status.open_condition_count}")
        if status.pending_actions:
            lines.append("Pending actions:")
            for action in status.pending_actions:
                lines.append(f"  - {action.description}")

    return "\n".join(lines)


@tool
async def lo_document_review(
    application_id: int,
    state: Annotated[dict, InjectedState],
) -> str:
    """List all documents for an application with their status, quality flags, and upload date.

    Args:
        application_id: The loan application ID.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        documents, total = await list_documents(session, user, application_id, limit=50)

    if total == 0:
        return f"No documents found for application {application_id}."

    lines = [f"Documents for application {application_id} ({total} total):"]
    for doc in documents:
        doc_type = doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type)
        status_val = doc.status.value if hasattr(doc.status, "value") else str(doc.status)
        line = f"- [{doc.id}] {doc_type}: {status_val}"

        if doc.quality_flags:
            try:
                flags = json.loads(doc.quality_flags)
                if isinstance(flags, list):
                    line += f" (issues: {', '.join(flags)})"
                else:
                    line += f" (issues: {doc.quality_flags})"
            except (json.JSONDecodeError, TypeError):
                line += f" (issues: {doc.quality_flags})"

        if doc.created_at:
            line += f" (uploaded: {doc.created_at.strftime('%Y-%m-%d')})"
        lines.append(line)

    return "\n".join(lines)


@tool
async def lo_document_quality(
    application_id: int,
    document_id: int,
    state: Annotated[dict, InjectedState],
) -> str:
    """Get detailed quality information for a specific document.

    Args:
        application_id: The loan application ID.
        document_id: The document ID to inspect.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        doc = await get_document(session, user, document_id)

    if doc is None:
        return "Document not found or you don't have access to it."

    if doc.application_id != application_id:
        return "Document does not belong to this application."

    doc_type = doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type)
    status_val = doc.status.value if hasattr(doc.status, "value") else str(doc.status)

    lines = [
        f"Document #{document_id} Detail:",
        f"Type: {doc_type}",
        f"Status: {status_val}",
    ]

    if doc.quality_flags:
        try:
            flags = json.loads(doc.quality_flags)
            if isinstance(flags, list) and flags:
                lines.append("Quality issues:")
                for flag in flags:
                    lines.append(f"  - {flag}")
            elif doc.quality_flags:
                lines.append(f"Quality notes: {doc.quality_flags}")
        except (json.JSONDecodeError, TypeError):
            lines.append(f"Quality notes: {doc.quality_flags}")
    else:
        lines.append("Quality: No issues detected")

    if doc.created_at:
        lines.append(f"Uploaded: {doc.created_at.strftime('%Y-%m-%d %H:%M')}")

    return "\n".join(lines)


@tool
async def lo_completeness_check(
    application_id: int,
    state: Annotated[dict, InjectedState],
) -> str:
    """Check document completeness for an application from the loan officer's perspective.

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
        if req.status:
            line += f" ({req.status.value})"
        if req.quality_flags:
            line += f" [issues: {', '.join(req.quality_flags)}]"
        lines.append(line)

    return "\n".join(lines)


@tool
async def lo_mark_resubmission(
    application_id: int,
    document_id: int,
    reason: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """Flag a document for resubmission by the borrower, with a reason.

    Only documents that have been processed (PROCESSING_COMPLETE, PENDING_REVIEW,
    or ACCEPTED) can be flagged. The borrower will be notified to upload a
    replacement.

    Args:
        application_id: The loan application ID.
        document_id: The document ID to flag.
        reason: Explanation of why the document needs resubmission.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        try:
            doc = await update_document_status(
                session,
                user,
                application_id,
                document_id,
                DocumentStatus.FLAGGED_FOR_RESUBMISSION,
                reason=reason,
            )
        except ValueError as e:
            return str(e)

        if doc is None:
            return "Document not found, not in this application, or you don't have access."

        await write_audit_event(
            session,
            event_type="document_flagged_for_resubmission",
            user_id=user.user_id,
            user_role=user.role.value,
            application_id=application_id,
            event_data={
                "document_id": document_id,
                "reason": reason,
            },
        )
        await session.commit()

    return (
        f"Document #{document_id} has been flagged for resubmission. "
        f"Reason: {reason}. The borrower will be notified."
    )


@tool
async def lo_underwriting_readiness(
    application_id: int,
    state: Annotated[dict, InjectedState],
) -> str:
    """Check whether an application is ready to be submitted to underwriting.

    Reviews stage, document completeness, processing status, and quality
    flags. Returns a clear verdict with any blockers that must be resolved.

    Args:
        application_id: The loan application ID to check.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        result = await check_underwriting_readiness(session, user, application_id)

    if result is None:
        return "Application not found or you don't have access to it."

    if result["is_ready"]:
        return (
            f"Application {application_id} is READY for underwriting submission. "
            "All documents are complete, processed, and have no quality issues. "
            "Would you like to submit it?"
        )

    lines = [
        f"Application {application_id} is NOT ready for underwriting. Blockers:",
    ]
    for blocker in result["blockers"]:
        lines.append(f"  - {blocker}")
    lines.append("")
    lines.append("Resolve these issues before submitting to underwriting.")

    return "\n".join(lines)


@tool
async def lo_submit_to_underwriting(
    application_id: int,
    state: Annotated[dict, InjectedState],
) -> str:
    """Submit an application to underwriting.

    This performs a two-step stage transition: APPLICATION -> PROCESSING ->
    UNDERWRITING. The state machine requires PROCESSING as an intermediate
    stage. Both transitions are audited.

    Note: When the Processor persona is added in a future phase, this tool
    would only transition to PROCESSING; the Processor would then prep the
    loan file and submit to UNDERWRITING.

    Readiness is checked first -- if blockers exist, the submission is
    refused with details.

    Args:
        application_id: The loan application ID to submit.
    """
    user = _user_context_from_state(state)
    async with SessionLocal() as session:
        # Gate: check readiness
        readiness = await check_underwriting_readiness(session, user, application_id)
        if readiness is None:
            return "Application not found or you don't have access to it."

        if not readiness["is_ready"]:
            lines = ["Cannot submit -- application is not ready:"]
            for b in readiness["blockers"]:
                lines.append(f"  - {b}")
            return "\n".join(lines)

        # Step 1: APPLICATION -> PROCESSING
        app = await transition_stage(session, user, application_id, ApplicationStage.PROCESSING)
        if app is None:
            return "Failed to transition to processing stage."

        await write_audit_event(
            session,
            event_type="stage_transition",
            user_id=user.user_id,
            user_role=user.role.value,
            application_id=application_id,
            event_data={
                "from_stage": "application",
                "to_stage": "processing",
                "action": "lo_submit_to_underwriting",
            },
        )

        # Step 2: PROCESSING -> UNDERWRITING
        app = await transition_stage(session, user, application_id, ApplicationStage.UNDERWRITING)
        if app is None:
            return "Failed to transition to underwriting stage."

        await write_audit_event(
            session,
            event_type="stage_transition",
            user_id=user.user_id,
            user_role=user.role.value,
            application_id=application_id,
            event_data={
                "from_stage": "processing",
                "to_stage": "underwriting",
                "action": "lo_submit_to_underwriting",
            },
        )
        await session.commit()

    return (
        f"Application {application_id} has been submitted to underwriting. "
        "Stage: UNDERWRITING. The underwriting team will review and may "
        "issue conditions."
    )
