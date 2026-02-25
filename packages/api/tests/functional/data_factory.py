# This project was developed with assistance from AI tools.
"""Centralized mock data portfolio for functional tests.

Produces consistent mock ORM objects shared across all persona tests:
- 2 borrowers (Sarah, Michael) with PII
- 3 applications at different stages and assignments
- Documents for application 101

All IDs are fixed so persona tests can reference them by number.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from db.enums import (
    ApplicationStage,
    DocumentStatus,
    DocumentType,
    LoanType,
)

from .personas import LO_USER_ID, MICHAEL_USER_ID, SARAH_USER_ID

# ---------------------------------------------------------------------------
# Borrowers
# ---------------------------------------------------------------------------


def make_borrower_sarah() -> MagicMock:
    b = MagicMock()
    b.id = 1
    b.keycloak_user_id = SARAH_USER_ID
    b.first_name = "Sarah"
    b.last_name = "Mitchell"
    b.email = "sarah@example.com"
    b.ssn_encrypted = "123-45-6789"
    b.dob = datetime(1990, 3, 15, tzinfo=UTC)
    b.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    b.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    return b


def make_borrower_michael() -> MagicMock:
    b = MagicMock()
    b.id = 2
    b.keycloak_user_id = MICHAEL_USER_ID
    b.first_name = "Michael"
    b.last_name = "Chen"
    b.email = "michael@example.com"
    b.ssn_encrypted = "987-65-4321"
    b.dob = datetime(1985, 7, 22, tzinfo=UTC)
    b.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    b.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    return b


def _make_app_borrower(borrower, *, is_primary=True) -> MagicMock:
    """Build a mock ApplicationBorrower junction object."""
    ab = MagicMock()
    ab.borrower = borrower
    ab.borrower_id = borrower.id
    ab.is_primary = is_primary
    return ab


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------


def make_app_sarah_1() -> MagicMock:
    """App 101: Sarah, APPLICATION stage, assigned to LO."""
    app = MagicMock()
    app.id = 101
    app.stage = ApplicationStage.APPLICATION
    app.loan_type = LoanType.CONVENTIONAL_30
    app.property_address = "123 Oak Street"
    app.loan_amount = Decimal("350000.00")
    app.property_value = Decimal("450000.00")
    app.assigned_to = LO_USER_ID
    app.created_at = datetime(2026, 1, 10, tzinfo=UTC)
    app.updated_at = datetime(2026, 1, 15, tzinfo=UTC)
    app.application_borrowers = [_make_app_borrower(make_borrower_sarah())]
    return app


def make_app_sarah_2() -> MagicMock:
    """App 102: Sarah, INQUIRY stage, unassigned."""
    app = MagicMock()
    app.id = 102
    app.stage = ApplicationStage.INQUIRY
    app.loan_type = None
    app.property_address = None
    app.loan_amount = None
    app.property_value = None
    app.assigned_to = None
    app.created_at = datetime(2026, 2, 1, tzinfo=UTC)
    app.updated_at = datetime(2026, 2, 1, tzinfo=UTC)
    app.application_borrowers = [_make_app_borrower(make_borrower_sarah())]
    return app


def make_app_michael() -> MagicMock:
    """App 103: Michael, UNDERWRITING stage, assigned to LO."""
    app = MagicMock()
    app.id = 103
    app.stage = ApplicationStage.UNDERWRITING
    app.loan_type = LoanType.FHA
    app.property_address = "456 Maple Avenue"
    app.loan_amount = Decimal("275000.00")
    app.property_value = Decimal("320000.00")
    app.assigned_to = LO_USER_ID
    app.created_at = datetime(2026, 1, 20, tzinfo=UTC)
    app.updated_at = datetime(2026, 2, 10, tzinfo=UTC)
    app.application_borrowers = [_make_app_borrower(make_borrower_michael())]
    return app


# ---------------------------------------------------------------------------
# Projection helpers
# ---------------------------------------------------------------------------


def all_applications() -> list[MagicMock]:
    """All 3 applications (CEO/underwriter/admin view)."""
    return [make_app_sarah_1(), make_app_sarah_2(), make_app_michael()]


def sarah_applications() -> list[MagicMock]:
    """Sarah's 2 applications (borrower_sarah view)."""
    return [make_app_sarah_1(), make_app_sarah_2()]


def michael_applications() -> list[MagicMock]:
    """Michael's 1 application (borrower_michael view)."""
    return [make_app_michael()]


def lo_assigned_applications() -> list[MagicMock]:
    """Apps assigned to the LO: 101 + 103 (102 is unassigned)."""
    return [make_app_sarah_1(), make_app_michael()]


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


def make_document(**overrides) -> MagicMock:
    """Build a mock Document ORM object with sensible defaults."""
    doc = MagicMock()
    doc.id = overrides.get("id", 1)
    doc.application_id = overrides.get("application_id", 101)
    doc.borrower_id = overrides.get("borrower_id", 1)
    doc.doc_type = overrides.get("doc_type", DocumentType.W2)
    doc.status = overrides.get("status", DocumentStatus.UPLOADED)
    doc.quality_flags = overrides.get("quality_flags", None)
    doc.uploaded_by = overrides.get("uploaded_by", "james.torres")
    doc.file_path = overrides.get("file_path", "/uploads/w2-2024.pdf")
    doc.created_at = overrides.get(
        "created_at",
        datetime(2026, 1, 15, tzinfo=UTC),
    )
    doc.updated_at = overrides.get(
        "updated_at",
        datetime(2026, 1, 15, tzinfo=UTC),
    )
    # Relationship for join-based scope filtering
    doc.application = make_app_sarah_1()
    return doc


def app_101_documents() -> list[MagicMock]:
    """Documents for application 101."""
    return [
        make_document(id=1, doc_type=DocumentType.W2),
        make_document(id=2, doc_type=DocumentType.PAY_STUB, file_path="/uploads/paystub.pdf"),
    ]
