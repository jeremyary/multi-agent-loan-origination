# This project was developed with assistance from AI tools.
"""Condition service for condition lifecycle management.

Handles listing conditions (with data scope), recording borrower text
responses, linking uploaded documents, checking document-based satisfaction,
and underwriter lifecycle operations (issue, review, clear, waive, return).
"""

import json
import logging
from datetime import datetime

from db import (
    Application,
    Condition,
    ConditionSeverity,
    ConditionStatus,
    Document,
    DocumentExtraction,
)
from db.enums import ApplicationStage
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.auth import UserContext
from ..services.application import get_application
from ..services.audit import write_audit_event

logger = logging.getLogger(__name__)


def _parse_quality_flags(raw: str | None) -> list[str]:
    """Parse quality_flags stored as JSON array or plain CSV string."""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(f) for f in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    return [f.strip() for f in raw.split(",") if f.strip()]


async def get_conditions(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
    *,
    open_only: bool = False,
) -> list[dict] | None:
    """Return conditions for an application, respecting data scope.

    Returns None if the application is not found or out of scope.
    Returns a list of condition dicts otherwise (may be empty).
    """
    app = await get_application(session, user, application_id)
    if app is None:
        return None

    # Query conditions for this application
    cond_stmt = select(Condition).where(Condition.application_id == application_id)
    if open_only:
        cond_stmt = cond_stmt.where(
            Condition.status.in_([ConditionStatus.OPEN, ConditionStatus.RESPONDED])
        )
    cond_stmt = cond_stmt.order_by(Condition.created_at)
    cond_result = await session.execute(cond_stmt)
    conditions = cond_result.scalars().all()

    return [
        {
            "id": c.id,
            "description": c.description,
            "severity": c.severity.value if c.severity else None,
            "status": c.status.value if c.status else None,
            "response_text": c.response_text,
            "issued_by": c.issued_by,
            "cleared_by": c.cleared_by,
            "due_date": c.due_date.isoformat() if c.due_date else None,
            "iteration_count": c.iteration_count or 0,
            "waiver_rationale": c.waiver_rationale,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in conditions
    ]


async def respond_to_condition(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
    condition_id: int,
    response_text: str,
) -> dict | None:
    """Record a borrower's text response to a condition.

    Returns the updated condition dict, or None if not found / out of scope.
    Updates status to RESPONDED if currently OPEN.
    """
    app = await get_application(session, user, application_id)
    if app is None:
        return None

    # Fetch the condition
    cond_stmt = select(Condition).where(
        Condition.id == condition_id,
        Condition.application_id == application_id,
    )
    cond_result = await session.execute(cond_stmt)
    condition = cond_result.scalar_one_or_none()

    if condition is None:
        return None

    # Record response
    condition.response_text = response_text
    if condition.status == ConditionStatus.OPEN:
        condition.status = ConditionStatus.RESPONDED

    # Audit trail for borrower condition response
    await write_audit_event(
        session,
        event_type="condition_response",
        user_id=user.user_id,
        user_role=user.role.value,
        application_id=application_id,
        event_data={
            "condition_id": condition_id,
            "description": condition.description,
            "response_text": response_text,
        },
    )

    await session.commit()
    await session.refresh(condition)

    return {
        "id": condition.id,
        "description": condition.description,
        "status": condition.status.value,
        "response_text": condition.response_text,
    }


async def link_document_to_condition(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
    condition_id: int,
    document_id: int,
) -> dict | None:
    """Link a document to a condition and update status to RESPONDED.

    Returns the updated condition dict, or None if not found / out of scope.
    """
    app = await get_application(session, user, application_id)
    if app is None:
        return None

    # Fetch condition
    cond_stmt = select(Condition).where(
        Condition.id == condition_id,
        Condition.application_id == application_id,
    )
    cond_result = await session.execute(cond_stmt)
    condition = cond_result.scalar_one_or_none()

    if condition is None:
        return None

    # Fetch document (must belong to the same application)
    doc_stmt = select(Document).where(
        Document.id == document_id,
        Document.application_id == application_id,
    )
    doc_result = await session.execute(doc_stmt)
    document = doc_result.scalar_one_or_none()

    if document is None:
        return None

    # Link document to condition
    document.condition_id = condition_id

    # Update condition status if OPEN
    if condition.status == ConditionStatus.OPEN:
        condition.status = ConditionStatus.RESPONDED

    await session.commit()
    await session.refresh(condition)

    return {
        "id": condition.id,
        "description": condition.description,
        "status": condition.status.value,
        "document_id": document_id,
    }


async def check_condition_documents(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
    condition_id: int,
) -> dict | None:
    """Check documents linked to a condition and assess satisfaction.

    Returns None if the application or condition is not found / out of scope.
    Returns a dict with condition info, linked documents, extraction details,
    and quality issues for the agent to evaluate.
    """
    app = await get_application(session, user, application_id)
    if app is None:
        return None

    # Fetch condition
    cond_stmt = select(Condition).where(
        Condition.id == condition_id,
        Condition.application_id == application_id,
    )
    cond_result = await session.execute(cond_stmt)
    condition = cond_result.scalar_one_or_none()

    if condition is None:
        return None

    # Fetch documents linked to this condition
    doc_stmt = (
        select(Document)
        .where(Document.condition_id == condition_id)
        .order_by(Document.created_at.desc())
    )
    doc_result = await session.execute(doc_stmt)
    documents = doc_result.scalars().all()

    doc_details = []
    for doc in documents:
        # Fetch extractions for each document
        ext_stmt = (
            select(DocumentExtraction)
            .where(DocumentExtraction.document_id == doc.id)
            .order_by(DocumentExtraction.field_name)
        )
        ext_result = await session.execute(ext_stmt)
        extractions = ext_result.scalars().all()

        doc_details.append(
            {
                "id": doc.id,
                "file_path": doc.file_path,
                "doc_type": doc.doc_type.value if doc.doc_type else None,
                "status": doc.status.value if doc.status else None,
                "quality_flags": _parse_quality_flags(doc.quality_flags),
                "extractions": [
                    {
                        "field": e.field_name,
                        "value": e.field_value,
                        "confidence": e.confidence,
                    }
                    for e in extractions
                ],
            }
        )

    return {
        "condition_id": condition.id,
        "description": condition.description,
        "status": condition.status.value if condition.status else None,
        "response_text": condition.response_text,
        "documents": doc_details,
        "has_documents": len(doc_details) > 0,
        "has_quality_issues": any(d["quality_flags"] for d in doc_details),
    }


# ---------------------------------------------------------------------------
# Underwriter lifecycle management
# ---------------------------------------------------------------------------

_TERMINAL_STATUSES = frozenset({ConditionStatus.CLEARED, ConditionStatus.WAIVED})
_WAIVABLE_SEVERITIES = frozenset(
    {ConditionSeverity.PRIOR_TO_CLOSING, ConditionSeverity.PRIOR_TO_FUNDING}
)
_CONDITION_STAGES = frozenset(
    {ApplicationStage.UNDERWRITING, ApplicationStage.CONDITIONAL_APPROVAL}
)


async def _fetch_condition(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
    condition_id: int,
) -> tuple[Application | None, Condition | None]:
    """Fetch an application + condition, respecting data scope.

    Returns (app, condition). Either may be None if not found / out of scope.
    """
    app = await get_application(session, user, application_id)
    if app is None:
        return None, None

    cond_stmt = select(Condition).where(
        Condition.id == condition_id,
        Condition.application_id == application_id,
    )
    cond_result = await session.execute(cond_stmt)
    condition = cond_result.scalar_one_or_none()
    return app, condition


async def issue_condition(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
    description: str,
    severity: ConditionSeverity,
    due_date: datetime | None = None,
) -> dict | None:
    """Issue a new condition on an application.

    Returns the created condition dict, None if application not found,
    or a dict with an ``"error"`` key if a business rule is violated.
    """
    app = await get_application(session, user, application_id)
    if app is None:
        return None

    if app.stage not in _CONDITION_STAGES:
        stage_val = app.stage.value if app.stage else "unknown"
        return {
            "error": (
                f"Conditions can only be issued during underwriting or conditional "
                f"approval. Application #{application_id} is in "
                f"{stage_val.replace('_', ' ').title()}."
            )
        }

    condition = Condition(
        application_id=application_id,
        description=description,
        severity=severity,
        status=ConditionStatus.OPEN,
        issued_by=user.user_id,
        due_date=due_date,
        iteration_count=0,
    )
    session.add(condition)

    await write_audit_event(
        session,
        event_type="condition_issued",
        user_id=user.user_id,
        user_role=user.role.value,
        application_id=application_id,
        event_data={
            "description": description,
            "severity": severity.value,
            "due_date": due_date.isoformat() if due_date else None,
        },
    )

    await session.commit()
    await session.refresh(condition)

    return {
        "id": condition.id,
        "description": condition.description,
        "severity": condition.severity.value,
        "status": condition.status.value,
        "due_date": condition.due_date.isoformat() if condition.due_date else None,
    }


async def review_condition(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
    condition_id: int,
) -> dict | None:
    """Move a condition from RESPONDED to UNDER_REVIEW.

    Returns the updated condition dict, None if not found,
    or a dict with an ``"error"`` key if a business rule is violated.
    """
    app, condition = await _fetch_condition(session, user, application_id, condition_id)
    if app is None:
        return None
    if condition is None:
        return None

    if condition.status != ConditionStatus.RESPONDED:
        return {
            "error": (
                f"Condition #{condition_id} is '{condition.status.value}' -- "
                f"only RESPONDED conditions can be moved to review."
            )
        }

    condition.status = ConditionStatus.UNDER_REVIEW

    await write_audit_event(
        session,
        event_type="condition_review_started",
        user_id=user.user_id,
        user_role=user.role.value,
        application_id=application_id,
        event_data={"condition_id": condition_id},
    )

    await session.commit()
    await session.refresh(condition)

    return {
        "id": condition.id,
        "description": condition.description,
        "status": condition.status.value,
    }


async def clear_condition(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
    condition_id: int,
) -> dict | None:
    """Clear a condition (RESPONDED or UNDER_REVIEW -> CLEARED).

    Returns the updated condition dict, None if not found,
    or a dict with an ``"error"`` key if a business rule is violated.
    """
    app, condition = await _fetch_condition(session, user, application_id, condition_id)
    if app is None:
        return None
    if condition is None:
        return None

    allowed = frozenset({ConditionStatus.RESPONDED, ConditionStatus.UNDER_REVIEW})
    if condition.status not in allowed:
        return {
            "error": (
                f"Condition #{condition_id} is '{condition.status.value}' -- "
                f"only RESPONDED or UNDER_REVIEW conditions can be cleared."
            )
        }

    condition.status = ConditionStatus.CLEARED
    condition.cleared_by = user.user_id

    await write_audit_event(
        session,
        event_type="condition_cleared",
        user_id=user.user_id,
        user_role=user.role.value,
        application_id=application_id,
        event_data={"condition_id": condition_id, "cleared_by": user.user_id},
    )

    await session.commit()
    await session.refresh(condition)

    return {
        "id": condition.id,
        "description": condition.description,
        "status": condition.status.value,
        "cleared_by": condition.cleared_by,
    }


async def waive_condition(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
    condition_id: int,
    rationale: str,
) -> dict | None:
    """Waive a condition (non-terminal, PRIOR_TO_CLOSING/FUNDING only).

    Returns the updated condition dict, None if not found,
    or a dict with an ``"error"`` key if a business rule is violated.
    """
    app, condition = await _fetch_condition(session, user, application_id, condition_id)
    if app is None:
        return None
    if condition is None:
        return None

    if condition.status in _TERMINAL_STATUSES:
        return {
            "error": (
                f"Condition #{condition_id} is already '{condition.status.value}' -- "
                f"terminal conditions cannot be waived."
            )
        }

    if condition.severity not in _WAIVABLE_SEVERITIES:
        return {
            "error": (
                f"Condition #{condition_id} has severity '{condition.severity.value}' -- "
                f"only PRIOR_TO_CLOSING and PRIOR_TO_FUNDING conditions can be waived."
            )
        }

    condition.status = ConditionStatus.WAIVED
    condition.waiver_rationale = rationale
    condition.cleared_by = user.user_id

    await write_audit_event(
        session,
        event_type="condition_waived",
        user_id=user.user_id,
        user_role=user.role.value,
        application_id=application_id,
        event_data={
            "condition_id": condition_id,
            "rationale": rationale,
            "severity": condition.severity.value,
        },
    )

    await session.commit()
    await session.refresh(condition)

    return {
        "id": condition.id,
        "description": condition.description,
        "status": condition.status.value,
        "waiver_rationale": condition.waiver_rationale,
        "cleared_by": condition.cleared_by,
    }


async def return_condition(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
    condition_id: int,
    note: str,
) -> dict | None:
    """Return a condition to the borrower (UNDER_REVIEW -> OPEN).

    Appends the note to response_text and increments iteration_count.
    Returns the updated condition dict, None if not found,
    or a dict with an ``"error"`` key if a business rule is violated.
    """
    app, condition = await _fetch_condition(session, user, application_id, condition_id)
    if app is None:
        return None
    if condition is None:
        return None

    if condition.status != ConditionStatus.UNDER_REVIEW:
        return {
            "error": (
                f"Condition #{condition_id} is '{condition.status.value}' -- "
                f"only UNDER_REVIEW conditions can be returned."
            )
        }

    condition.status = ConditionStatus.OPEN
    condition.iteration_count = (condition.iteration_count or 0) + 1

    # Append return note to response_text
    return_note = f"[Return #{condition.iteration_count}]: {note}"
    if condition.response_text:
        condition.response_text = f"{condition.response_text}\n{return_note}"
    else:
        condition.response_text = return_note

    await write_audit_event(
        session,
        event_type="condition_returned",
        user_id=user.user_id,
        user_role=user.role.value,
        application_id=application_id,
        event_data={
            "condition_id": condition_id,
            "note": note,
            "iteration": condition.iteration_count,
        },
    )

    await session.commit()
    await session.refresh(condition)

    return {
        "id": condition.id,
        "description": condition.description,
        "status": condition.status.value,
        "iteration_count": condition.iteration_count,
        "response_text": condition.response_text,
    }


async def get_condition_summary(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
) -> dict | None:
    """Get a summary of condition counts by status for an application.

    Returns None if the application is not found or out of scope.
    Returns a dict with status counts and total.
    """
    app = await get_application(session, user, application_id)
    if app is None:
        return None

    stmt = (
        select(Condition.status, func.count(Condition.id))
        .where(Condition.application_id == application_id)
        .group_by(Condition.status)
    )
    result = await session.execute(stmt)
    rows = result.all()

    counts = {status.value: 0 for status in ConditionStatus}
    total = 0
    for status, count in rows:
        counts[status.value] = count
        total += count

    return {"counts": counts, "total": total}
