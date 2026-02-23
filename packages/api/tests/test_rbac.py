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


def test_mask_application_pii_masks_borrower():
    """Application-level masking applies to nested borrower fields."""
    app_dict = {
        "id": 1,
        "borrower": {
            "id": 10,
            "first_name": "Sarah",
            "last_name": "Mitchell",
            "ssn_encrypted": "123-45-6789",
            "dob": "1990-03-15T00:00:00",
            "email": "sarah@example.com",
        },
        "stage": "inquiry",
    }
    masked = mask_application_pii(app_dict)
    # Names stay visible
    assert masked["borrower"]["first_name"] == "Sarah"
    assert masked["borrower"]["last_name"] == "Mitchell"
    # PII is masked
    assert masked["borrower"]["ssn_encrypted"] == "***-**-6789"
    assert masked["borrower"]["dob"] == "1990-**-**"
    # Original not mutated
    assert app_dict["borrower"]["ssn_encrypted"] == "123-45-6789"


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
