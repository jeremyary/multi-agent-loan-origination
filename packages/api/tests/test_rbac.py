# This project was developed with assistance from AI tools.
"""Tests for RBAC enforcement on application routes and PII masking."""

from src.middleware.pii import mask_application_pii, mask_dob, mask_ssn

# ---------------------------------------------------------------------------
# PII masking
# ---------------------------------------------------------------------------


def test_mask_ssn_standard_format():
    """SSN masked to ***-**-NNNN with last 4 visible."""
    assert mask_ssn("123-45-6789") == "***-**-6789"


def test_mask_dob_iso_datetime():
    """DOB masked to YYYY-**-** with only year visible."""
    assert mask_dob("1990-03-15T00:00:00") == "1990-**-**"


def test_mask_application_pii_masks_borrowers_list():
    """Application-level masking applies to borrowers list."""
    app_dict = {
        "id": 1,
        "borrowers": [
            {
                "id": 10,
                "first_name": "Sarah",
                "last_name": "Mitchell",
                "ssn_encrypted": "123-45-6789",
                "dob": "1990-03-15T00:00:00",
                "email": "sarah@example.com",
                "is_primary": True,
            },
            {
                "id": 11,
                "first_name": "Jennifer",
                "last_name": "Mitchell",
                "ssn_encrypted": "987-65-4321",
                "dob": "1992-08-22T00:00:00",
                "email": "jennifer@example.com",
                "is_primary": False,
            },
        ],
        "stage": "inquiry",
    }
    masked = mask_application_pii(app_dict)
    # Names stay visible
    assert masked["borrowers"][0]["first_name"] == "Sarah"
    assert masked["borrowers"][1]["first_name"] == "Jennifer"
    # PII is masked
    assert masked["borrowers"][0]["ssn_encrypted"] == "***-**-6789"
    assert masked["borrowers"][0]["dob"] == "1990-**-**"
    assert masked["borrowers"][1]["ssn_encrypted"] == "***-**-4321"
    assert masked["borrowers"][1]["dob"] == "1992-**-**"
    # Original not mutated
    assert app_dict["borrowers"][0]["ssn_encrypted"] == "123-45-6789"


# ---------------------------------------------------------------------------
# Route-level RBAC
# ---------------------------------------------------------------------------


def test_prospect_cannot_access_applications(monkeypatch):
    """Prospect role gets 403 on application routes."""
    from db.enums import UserRole
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.core.config import settings
    from src.middleware.auth import get_current_user
    from src.schemas.auth import DataScope, UserContext

    monkeypatch.setattr(settings, "AUTH_DISABLED", False)

    app = FastAPI()

    prospect = UserContext(
        user_id="prospect-1",
        role=UserRole.PROSPECT,
        email="visitor@example.com",
        name="Visitor",
        data_scope=DataScope(),
    )

    async def fake_user():
        return prospect

    from src.routes.applications import router

    app.include_router(router, prefix="/api/applications")
    app.dependency_overrides[get_current_user] = fake_user

    client = TestClient(app)
    resp = client.get("/api/applications/")
    assert resp.status_code == 403


def test_co_borrower_sees_shared_application(monkeypatch):
    """Co-borrower (non-primary) sees application via junction table scope."""
    from unittest.mock import AsyncMock, MagicMock

    from db import get_db
    from db.enums import ApplicationStage, LoanType, UserRole
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.core.config import settings
    from src.middleware.auth import get_current_user
    from src.routes.applications import router
    from src.schemas.auth import DataScope, UserContext

    monkeypatch.setattr(settings, "AUTH_DISABLED", False)

    # Co-borrower (not the primary on this app)
    co_borrower = UserContext(
        user_id="coborrower-1",
        role=UserRole.BORROWER,
        email="coborrower@example.com",
        name="Co-Borrower",
        data_scope=DataScope(own_data_only=True, user_id="coborrower-1"),
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/applications")

    async def fake_user():
        return co_borrower

    mock_session = AsyncMock()

    # Build mock application with both primary and co-borrower in junction table
    mock_app = MagicMock()
    mock_app.id = 101
    mock_app.stage = ApplicationStage.APPLICATION
    mock_app.loan_type = LoanType.CONVENTIONAL_30
    mock_app.property_address = "123 Test St"
    mock_app.loan_amount = 300000
    mock_app.property_value = 400000
    mock_app.assigned_to = None
    mock_app.created_at = "2026-01-01T00:00:00+00:00"
    mock_app.updated_at = "2026-01-01T00:00:00+00:00"

    # Junction entries: primary + co-borrower
    primary_borrower = MagicMock()
    primary_borrower.id = 1
    primary_borrower.first_name = "Primary"
    primary_borrower.last_name = "Borrower"
    primary_borrower.email = "primary@example.com"
    primary_borrower.ssn_encrypted = None
    primary_borrower.dob = None

    co_borrower_obj = MagicMock()
    co_borrower_obj.id = 2
    co_borrower_obj.first_name = "Co"
    co_borrower_obj.last_name = "Borrower"
    co_borrower_obj.email = "coborrower@example.com"
    co_borrower_obj.ssn_encrypted = None
    co_borrower_obj.dob = None

    ab_primary = MagicMock()
    ab_primary.borrower = primary_borrower
    ab_primary.is_primary = True

    ab_co = MagicMock()
    ab_co.borrower = co_borrower_obj
    ab_co.is_primary = False

    mock_app.application_borrowers = [ab_primary, ab_co]
    mock_app.financials = None

    # Mock session returns: count=1, then the app
    count_result = MagicMock()
    count_result.scalar.return_value = 1
    list_result = MagicMock()
    list_result.unique.return_value.scalars.return_value.all.return_value = [mock_app]
    mock_session.execute = AsyncMock(side_effect=[count_result, list_result])

    async def fake_db():
        yield mock_session

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_db] = fake_db

    client = TestClient(app)
    resp = client.get("/api/applications/")
    assert resp.status_code == 200

    data = resp.json()
    assert data["count"] == 1
    apps = data["data"]
    assert len(apps) == 1
    assert apps[0]["id"] == 101
    # Both borrowers in list with correct is_primary flags
    borrowers = apps[0]["borrowers"]
    assert len(borrowers) == 2
    primary_list = [b for b in borrowers if b["is_primary"]]
    co_list = [b for b in borrowers if not b["is_primary"]]
    assert len(primary_list) == 1
    assert len(co_list) == 1
    assert co_list[0]["first_name"] == "Co"


def test_borrower_cannot_patch_application(monkeypatch):
    """Borrowers can view but not update applications."""
    from db.enums import UserRole
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.core.config import settings
    from src.middleware.auth import get_current_user
    from src.schemas.auth import DataScope, UserContext

    monkeypatch.setattr(settings, "AUTH_DISABLED", False)

    app = FastAPI()

    borrower = UserContext(
        user_id="borrower-1",
        role=UserRole.BORROWER,
        email="borrower@example.com",
        name="Test Borrower",
        data_scope=DataScope(own_data_only=True, user_id="borrower-1"),
    )

    async def fake_user():
        return borrower

    from src.routes.applications import router

    app.include_router(router, prefix="/api/applications")
    app.dependency_overrides[get_current_user] = fake_user

    client = TestClient(app)
    resp = client.patch("/api/applications/1", json={"property_address": "123 Main St"})
    assert resp.status_code == 403
