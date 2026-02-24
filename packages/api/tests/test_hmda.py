# This project was developed with assistance from AI tools.
"""Tests for HMDA demographic data collection endpoint and isolation lint."""

import subprocess
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from db import get_compliance_db, get_db
from db.enums import UserRole
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
