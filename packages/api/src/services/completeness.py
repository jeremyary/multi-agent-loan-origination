# This project was developed with assistance from AI tools.
"""Document completeness checking service.

Determines which documents are required for a given loan type and employment
status, then compares against uploaded documents to produce a completeness
summary.
"""

import json
import logging

from db import Application, ApplicationBorrower, Document
from db.enums import DocumentStatus, DocumentType, EmploymentStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..schemas.auth import UserContext
from ..schemas.completeness import CompletenessResponse, DocumentRequirement
from ..services.scope import apply_data_scope

logger = logging.getLogger(__name__)

# Human-readable labels for document types
_DOC_TYPE_LABELS: dict[DocumentType, str] = {
    DocumentType.W2: "W-2 Form",
    DocumentType.PAY_STUB: "Recent Pay Stub",
    DocumentType.TAX_RETURN: "Tax Return",
    DocumentType.BANK_STATEMENT: "Bank Statement",
    DocumentType.ID: "Government-Issued ID",
    DocumentType.PROPERTY_APPRAISAL: "Property Appraisal",
    DocumentType.INSURANCE: "Homeowner's Insurance",
}

# Document requirements by loan_type and employment_status.
# Key structure: DOCUMENT_REQUIREMENTS[loan_type_value][employment_status_value]
# Falls back: specific -> loan_type + "_default" -> "_default" + "_default"
DOCUMENT_REQUIREMENTS: dict[str, dict[str, list[DocumentType]]] = {
    "_default": {
        "_default": [
            DocumentType.W2,
            DocumentType.PAY_STUB,
            DocumentType.BANK_STATEMENT,
            DocumentType.ID,
        ],
        EmploymentStatus.W2_EMPLOYEE.value: [
            DocumentType.W2,
            DocumentType.PAY_STUB,
            DocumentType.BANK_STATEMENT,
            DocumentType.ID,
        ],
        EmploymentStatus.SELF_EMPLOYED.value: [
            DocumentType.TAX_RETURN,
            DocumentType.BANK_STATEMENT,
            DocumentType.ID,
        ],
        EmploymentStatus.RETIRED.value: [
            DocumentType.TAX_RETURN,
            DocumentType.BANK_STATEMENT,
            DocumentType.ID,
        ],
        EmploymentStatus.UNEMPLOYED.value: [
            DocumentType.BANK_STATEMENT,
            DocumentType.ID,
        ],
        EmploymentStatus.OTHER.value: [
            DocumentType.TAX_RETURN,
            DocumentType.BANK_STATEMENT,
            DocumentType.ID,
        ],
    },
    "fha": {
        "_default": [
            DocumentType.W2,
            DocumentType.PAY_STUB,
            DocumentType.TAX_RETURN,
            DocumentType.BANK_STATEMENT,
            DocumentType.ID,
        ],
        EmploymentStatus.W2_EMPLOYEE.value: [
            DocumentType.W2,
            DocumentType.PAY_STUB,
            DocumentType.TAX_RETURN,
            DocumentType.BANK_STATEMENT,
            DocumentType.ID,
        ],
        EmploymentStatus.SELF_EMPLOYED.value: [
            DocumentType.TAX_RETURN,
            DocumentType.BANK_STATEMENT,
            DocumentType.ID,
        ],
        EmploymentStatus.RETIRED.value: [
            DocumentType.TAX_RETURN,
            DocumentType.BANK_STATEMENT,
            DocumentType.ID,
        ],
    },
    "va": {
        "_default": [
            DocumentType.W2,
            DocumentType.PAY_STUB,
            DocumentType.BANK_STATEMENT,
            DocumentType.ID,
        ],
        EmploymentStatus.W2_EMPLOYEE.value: [
            DocumentType.W2,
            DocumentType.PAY_STUB,
            DocumentType.BANK_STATEMENT,
            DocumentType.ID,
        ],
        EmploymentStatus.SELF_EMPLOYED.value: [
            DocumentType.TAX_RETURN,
            DocumentType.BANK_STATEMENT,
            DocumentType.ID,
        ],
    },
}

# Statuses that count as "not provided" for completeness purposes
_EXCLUDED_STATUSES = {
    DocumentStatus.REJECTED,
    DocumentStatus.FLAGGED_FOR_RESUBMISSION,
    DocumentStatus.PROCESSING_FAILED,
}


def _get_required_doc_types(
    loan_type: str | None,
    employment_status: str | None,
) -> list[DocumentType]:
    """Look up required doc types using fallback chain."""
    lt = loan_type or "_default"
    es = employment_status or "_default"

    # Try specific loan_type + employment_status
    loan_reqs = DOCUMENT_REQUIREMENTS.get(lt)
    if loan_reqs:
        reqs = loan_reqs.get(es)
        if reqs:
            return reqs
        # Try loan_type + _default
        reqs = loan_reqs.get("_default")
        if reqs:
            return reqs

    # Fall back to _default + employment_status
    default_reqs = DOCUMENT_REQUIREMENTS["_default"]
    reqs = default_reqs.get(es)
    if reqs:
        return reqs

    # Ultimate fallback: _default + _default
    return default_reqs["_default"]


async def check_completeness(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
) -> CompletenessResponse | None:
    """Check document completeness for an application.

    Returns None if the application is not found or not accessible.
    """
    # Load application with data scope filtering
    app_stmt = (
        select(Application)
        .options(
            selectinload(Application.application_borrowers).joinedload(ApplicationBorrower.borrower)
        )
        .where(Application.id == application_id)
    )
    app_stmt = apply_data_scope(app_stmt, user.data_scope, user)
    result = await session.execute(app_stmt)
    app = result.unique().scalar_one_or_none()
    if app is None:
        return None

    # Resolve primary borrower's employment status
    employment_status = None
    for ab in app.application_borrowers or []:
        if ab.is_primary and ab.borrower:
            employment_status = (
                ab.borrower.employment_status.value if ab.borrower.employment_status else None
            )
            break

    loan_type = app.loan_type.value if app.loan_type else None
    required_types = _get_required_doc_types(loan_type, employment_status)

    # Query documents for this app, excluding failed/rejected
    doc_stmt = select(Document).where(
        Document.application_id == application_id,
        Document.status.notin_([s.value for s in _EXCLUDED_STATUSES]),
    )
    doc_stmt = apply_data_scope(
        doc_stmt, user.data_scope, user, join_to_application=Document.application
    )
    doc_result = await session.execute(doc_stmt)
    documents = doc_result.scalars().all()

    # Build lookup: doc_type -> best document (most recent)
    doc_by_type: dict[DocumentType, Document] = {}
    for doc in documents:
        existing = doc_by_type.get(doc.doc_type)
        if existing is None or doc.created_at > existing.created_at:
            doc_by_type[doc.doc_type] = doc

    # Build requirements list
    requirements: list[DocumentRequirement] = []
    provided_count = 0
    for dt in required_types:
        doc = doc_by_type.get(dt)
        if doc:
            flags = []
            if doc.quality_flags:
                try:
                    flags = json.loads(doc.quality_flags)
                except (json.JSONDecodeError, TypeError):
                    flags = []
            requirements.append(
                DocumentRequirement(
                    doc_type=dt,
                    label=_DOC_TYPE_LABELS.get(dt, dt.value),
                    is_provided=True,
                    document_id=doc.id,
                    status=doc.status,
                    quality_flags=flags,
                )
            )
            provided_count += 1
        else:
            requirements.append(
                DocumentRequirement(
                    doc_type=dt,
                    label=_DOC_TYPE_LABELS.get(dt, dt.value),
                    is_provided=False,
                )
            )

    return CompletenessResponse(
        application_id=application_id,
        is_complete=provided_count == len(required_types),
        requirements=requirements,
        provided_count=provided_count,
        required_count=len(required_types),
    )
