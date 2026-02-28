# This project was developed with assistance from AI tools.
"""Tests for JWT authentication middleware."""

import pytest
from db.enums import UserRole
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.core.config import settings
from src.middleware.auth import CurrentUser, _resolve_role, require_roles
from src.schemas.auth import TokenPayload

# ---------------------------------------------------------------------------
# AUTH_DISABLED bypass
# ---------------------------------------------------------------------------


def test_auth_disabled_returns_dev_admin(monkeypatch):
    """When AUTH_DISABLED=true, any request gets a dev admin user."""
    monkeypatch.setattr(settings, "AUTH_DISABLED", True)

    app = FastAPI()

    @app.get("/me")
    async def me(user: CurrentUser):
        return {"user_id": user.user_id, "role": user.role.value}

    test_client = TestClient(app)
    resp = test_client.get("/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == "dev-user"
    assert body["role"] == "admin"


# ---------------------------------------------------------------------------
# Missing / malformed token
# ---------------------------------------------------------------------------


def test_missing_token_returns_401(monkeypatch):
    """A request with no Authorization header should get 401."""
    monkeypatch.setattr(settings, "AUTH_DISABLED", False)

    app = FastAPI()

    @app.get("/me")
    async def me(user: CurrentUser):
        return {}

    test_client = TestClient(app)
    resp = test_client.get("/me")
    assert resp.status_code == 401
    assert "Missing authentication token" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Role resolution
# ---------------------------------------------------------------------------


def test_resolve_role_picks_known_role():
    """_resolve_role returns the first known role from token claims."""
    payload = TokenPayload(
        sub="user-1",
        realm_access={"roles": ["offline_access", "loan_officer", "uma_authorization"]},
    )
    role = _resolve_role(payload)
    assert role == UserRole.LOAN_OFFICER


def test_resolve_role_no_known_role_raises_value_error():
    """_resolve_role raises ValueError when no recognized roles are present."""
    payload = TokenPayload(
        sub="user-1",
        realm_access={"roles": ["offline_access", "uma_authorization"]},
    )

    with pytest.raises(ValueError, match="No recognized role assigned"):
        _resolve_role(payload)


# ---------------------------------------------------------------------------
# require_roles dependency
# ---------------------------------------------------------------------------


def test_require_roles_rejects_wrong_role(monkeypatch):
    """require_roles returns 403 when user's role is not in allowed set."""
    monkeypatch.setattr(settings, "AUTH_DISABLED", True)

    app = FastAPI()

    check_underwriter = require_roles(UserRole.UNDERWRITER)

    @app.get("/uw-only", dependencies=[Depends(check_underwriter)])
    async def uw_only(user: CurrentUser):
        return {"ok": True}

    test_client = TestClient(app)
    # dev-user is admin, not underwriter
    resp = test_client.get("/uw-only")
    assert resp.status_code == 403
    assert "Insufficient permissions" in resp.json()["detail"]
