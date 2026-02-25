# This project was developed with assistance from AI tools.
"""Tests for HMDA demographic data collection, loan data snapshot, and isolation lint."""

import json
import subprocess
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from db import get_compliance_db, get_db
from db.enums import LoanType, UserRole
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.middleware.auth import get_current_user
from src.routes.hmda import router
from src.schemas.auth import DataScope, UserContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_BORROWER = UserContext(
    user_id="borrower-1",
    role=UserRole.BORROWER,
    email="borrower@example.com",
    name="Test Borrower",
    data_scope=DataScope(own_data_only=True, user_id="borrower-1"),
)


def _make_app(user: UserContext = _BORROWER):
    """Build a test app with mocked auth and db dependencies."""
    app = FastAPI()
    app.include_router(router, prefix="/api/hmda")

    async def fake_user():
        return user

    app.dependency_overrides[get_current_user] = fake_user
    return app


def _mock_sessions(
    application_exists: bool = True,
):
    """Create mocked lending and compliance sessions.

    Returns (app, client, lending_session, compliance_session).
    """
    app = _make_app()

    # Mock lending session -- used to verify application exists
    lending_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = 1 if application_exists else None
    lending_session.execute = AsyncMock(return_value=mock_result)

    # Mock compliance session -- used to write demographic + audit
    compliance_session = AsyncMock()
    # session.add() is synchronous in SQLAlchemy, use MagicMock to avoid warnings
    compliance_session.add = MagicMock()

    # After commit + refresh, the demographic gets an id and collected_at
    async def fake_refresh(obj):
        obj.id = 42
        obj.collected_at = datetime(2026, 2, 24, 12, 0, 0)

    compliance_session.refresh = fake_refresh

    async def fake_lending_db():
        yield lending_session

    async def fake_compliance_db():
        yield compliance_session

    app.dependency_overrides[get_db] = fake_lending_db
    app.dependency_overrides[get_compliance_db] = fake_compliance_db

    client = TestClient(app)
    return app, client, lending_session, compliance_session


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------


def test_collect_hmda_success():
    """POST /api/hmda/collect returns 201 with valid data."""
    _, client, _, compliance_session = _mock_sessions(application_exists=True)

    response = client.post(
        "/api/hmda/collect",
        json={
            "application_id": 1,
            "race": "White",
            "ethnicity": "Not Hispanic or Latino",
            "sex": "Female",
            "age": "35-44",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 42
    assert data["application_id"] == 1
    assert data["status"] == "collected"
    assert "collected_at" in data

    # Verify compliance session committed
    compliance_session.commit.assert_awaited_once()


def test_collect_hmda_missing_application():
    """POST /api/hmda/collect returns 404 when application doesn't exist."""
    _, client, _, _ = _mock_sessions(application_exists=False)

    response = client.post(
        "/api/hmda/collect",
        json={"application_id": 9999},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_collect_hmda_validation_error():
    """POST /api/hmda/collect returns 422 for missing required fields."""
    _, client, _, _ = _mock_sessions()

    response = client.post(
        "/api/hmda/collect",
        json={},
    )

    assert response.status_code == 422


def test_collect_hmda_partial_demographics():
    """POST /api/hmda/collect accepts partial data (only race, no ethnicity/sex)."""
    _, client, _, _ = _mock_sessions(application_exists=True)

    response = client.post(
        "/api/hmda/collect",
        json={
            "application_id": 1,
            "race": "Asian",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["application_id"] == 1
    assert data["status"] == "collected"


def test_prospect_cannot_collect_hmda(monkeypatch):
    """Prospect role gets 403 on HMDA collection."""
    from src.core.config import settings

    monkeypatch.setattr(settings, "AUTH_DISABLED", False)

    prospect = UserContext(
        user_id="prospect-1",
        role=UserRole.PROSPECT,
        email="visitor@example.com",
        name="Visitor",
        data_scope=DataScope(),
    )
    app = _make_app(user=prospect)

    async def fake_lending_db():
        yield AsyncMock()

    async def fake_compliance_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = fake_lending_db
    app.dependency_overrides[get_compliance_db] = fake_compliance_db

    client = TestClient(app)
    response = client.post(
        "/api/hmda/collect",
        json={"application_id": 1},
    )
    assert response.status_code == 403


def test_collect_hmda_with_age():
    """POST /api/hmda/collect stores age in demographics record."""
    _, client, _, compliance_session = _mock_sessions(application_exists=True)

    response = client.post(
        "/api/hmda/collect",
        json={
            "application_id": 1,
            "race": "Asian",
            "age": "25-34",
        },
    )

    assert response.status_code == 201

    # Check the HmdaDemographic was created with age
    hmda_call = compliance_session.add.call_args_list[0]
    hmda_obj = hmda_call[0][0]
    assert hmda_obj.age == "25-34"
    assert hmda_obj.race == "Asian"


# ---------------------------------------------------------------------------
# Snapshot loan data tests
# ---------------------------------------------------------------------------


def _mock_application(
    app_id=1,
    loan_type=LoanType.CONVENTIONAL_30,
    property_address="123 Main St, Denver, CO",
):
    """Build a mock Application ORM object."""
    app = MagicMock()
    app.id = app_id
    app.loan_type = loan_type
    app.property_address = property_address
    return app


def _mock_financials(
    app_id=1,
    gross_monthly_income=Decimal("8500.00"),
    dti_ratio=0.282,
    credit_score=742,
):
    """Build a mock ApplicationFinancials ORM object."""
    fin = MagicMock()
    fin.application_id = app_id
    fin.gross_monthly_income = gross_monthly_income
    fin.dti_ratio = dti_ratio
    fin.credit_score = credit_score
    return fin


@pytest.mark.asyncio
async def test_snapshot_loan_data():
    """snapshot_loan_data copies lending data to hmda.loan_data."""
    from src.services.compliance.hmda import snapshot_loan_data

    mock_app = _mock_application()
    mock_fin = _mock_financials()

    mock_lending_session = AsyncMock()
    # First execute returns Application, second returns Financials
    app_result = MagicMock()
    app_result.scalar_one_or_none.return_value = mock_app
    fin_result = MagicMock()
    fin_result.scalar_one_or_none.return_value = mock_fin
    mock_lending_session.execute = AsyncMock(side_effect=[app_result, fin_result])

    mock_compliance_session = AsyncMock()
    mock_compliance_session.add = MagicMock()
    # No existing loan_data row
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None
    mock_compliance_session.execute = AsyncMock(return_value=existing_result)

    with (
        patch("src.services.compliance.hmda.SessionLocal") as mock_lending_cls,
        patch("src.services.compliance.hmda.ComplianceSessionLocal") as mock_compliance_cls,
    ):
        mock_lending_cls.return_value.__aenter__ = AsyncMock(return_value=mock_lending_session)
        mock_lending_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_compliance_cls.return_value.__aenter__ = AsyncMock(
            return_value=mock_compliance_session
        )
        mock_compliance_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await snapshot_loan_data(1)

    # Should have added HmdaLoanData + AuditEvent
    assert mock_compliance_session.add.call_count == 2
    mock_compliance_session.commit.assert_called_once()

    # Check the HmdaLoanData object
    loan_data_call = mock_compliance_session.add.call_args_list[0]
    loan_data_obj = loan_data_call[0][0]
    assert loan_data_obj.application_id == 1
    assert loan_data_obj.gross_monthly_income == Decimal("8500.00")
    assert loan_data_obj.credit_score == 742
    assert loan_data_obj.loan_type == "conventional_30"
    assert loan_data_obj.property_location == "123 Main St, Denver, CO"


@pytest.mark.asyncio
async def test_snapshot_loan_data_audit_event():
    """snapshot_loan_data logs an audit event with snapshot details."""
    from src.services.compliance.hmda import snapshot_loan_data

    mock_app = _mock_application()
    mock_fin = _mock_financials()

    mock_lending_session = AsyncMock()
    app_result = MagicMock()
    app_result.scalar_one_or_none.return_value = mock_app
    fin_result = MagicMock()
    fin_result.scalar_one_or_none.return_value = mock_fin
    mock_lending_session.execute = AsyncMock(side_effect=[app_result, fin_result])

    mock_compliance_session = AsyncMock()
    mock_compliance_session.add = MagicMock()
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None
    mock_compliance_session.execute = AsyncMock(return_value=existing_result)

    with (
        patch("src.services.compliance.hmda.SessionLocal") as mock_lending_cls,
        patch("src.services.compliance.hmda.ComplianceSessionLocal") as mock_compliance_cls,
    ):
        mock_lending_cls.return_value.__aenter__ = AsyncMock(return_value=mock_lending_session)
        mock_lending_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_compliance_cls.return_value.__aenter__ = AsyncMock(
            return_value=mock_compliance_session
        )
        mock_compliance_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await snapshot_loan_data(1)

    # Second add call is the AuditEvent
    audit_call = mock_compliance_session.add.call_args_list[1]
    audit_obj = audit_call[0][0]
    assert audit_obj.event_type == "hmda_loan_data_snapshot"
    assert audit_obj.application_id == 1
    event_data = json.loads(audit_obj.event_data)
    assert "loan_type" in event_data["captured_fields"]
    assert "credit_score" in event_data["captured_fields"]
    assert "loan_purpose" in event_data["null_fields"]
    assert "interest_rate" in event_data["null_fields"]
    assert "total_fees" in event_data["null_fields"]
    assert event_data["is_update"] is False


@pytest.mark.asyncio
async def test_snapshot_loan_data_upserts():
    """Second snapshot call updates rather than duplicates."""
    from src.services.compliance.hmda import snapshot_loan_data

    mock_app = _mock_application()
    mock_fin = _mock_financials(credit_score=780)

    mock_lending_session = AsyncMock()
    app_result = MagicMock()
    app_result.scalar_one_or_none.return_value = mock_app
    fin_result = MagicMock()
    fin_result.scalar_one_or_none.return_value = mock_fin
    mock_lending_session.execute = AsyncMock(side_effect=[app_result, fin_result])

    # Simulate existing loan_data row
    existing_loan_data = MagicMock()
    existing_loan_data.application_id = 1
    existing_loan_data.credit_score = 742

    mock_compliance_session = AsyncMock()
    mock_compliance_session.add = MagicMock()
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = existing_loan_data
    mock_compliance_session.execute = AsyncMock(return_value=existing_result)

    with (
        patch("src.services.compliance.hmda.SessionLocal") as mock_lending_cls,
        patch("src.services.compliance.hmda.ComplianceSessionLocal") as mock_compliance_cls,
    ):
        mock_lending_cls.return_value.__aenter__ = AsyncMock(return_value=mock_lending_session)
        mock_lending_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_compliance_cls.return_value.__aenter__ = AsyncMock(
            return_value=mock_compliance_session
        )
        mock_compliance_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await snapshot_loan_data(1)

    # Should only add the AuditEvent (not a new HmdaLoanData)
    assert mock_compliance_session.add.call_count == 1
    # Existing object should have been updated
    assert existing_loan_data.credit_score == 780

    # Audit event should mark this as an update
    audit_call = mock_compliance_session.add.call_args_list[0]
    audit_obj = audit_call[0][0]
    event_data = json.loads(audit_obj.event_data)
    assert event_data["is_update"] is True


# ---------------------------------------------------------------------------
# Lint check test
# ---------------------------------------------------------------------------


def test_lint_hmda_isolation():
    """The HMDA isolation lint script passes on a clean codebase."""
    result = subprocess.run(
        ["bash", "scripts/lint-hmda-isolation.sh"],
        capture_output=True,
        text=True,
        cwd="/home/jary/redhat/git/mortgage-ai",
    )
    assert result.returncode == 0, f"HMDA isolation lint failed:\n{result.stdout}\n{result.stderr}"
