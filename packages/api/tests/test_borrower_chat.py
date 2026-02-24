# This project was developed with assistance from AI tools.
"""Tests for borrower assistant agent build, WS auth paths, and endpoint integration."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.config import settings
from src.main import app
from src.routes._chat_handler import authenticate_websocket


@pytest.fixture(autouse=True)
def _disable_auth(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_DISABLED", True)


@pytest.fixture
def client():
    return TestClient(app)


# -- Agent build --


def test_borrower_agent_builds():
    """should compile borrower-assistant graph without error."""
    from src.agents.registry import clear_agent_cache, get_agent

    clear_agent_cache()
    graph = get_agent("borrower-assistant")
    assert graph is not None
    clear_agent_cache()


# -- WebSocket authentication --


@pytest.mark.asyncio
async def test_authenticate_websocket_accepts_when_auth_disabled():
    """should return dev user with borrower role when AUTH_DISABLED=true."""
    from db.enums import UserRole

    ws = AsyncMock()
    ws.query_params = {}
    user = await authenticate_websocket(ws, required_role=UserRole.BORROWER)
    assert user is not None
    assert user.user_id == "dev-user"
    assert user.role == UserRole.BORROWER
    assert user.data_scope.own_data_only is True


@pytest.mark.asyncio
async def test_authenticate_websocket_rejects_no_token(monkeypatch):
    """should close WS with 4001 when token is missing and role required."""
    from db.enums import UserRole

    monkeypatch.setattr(settings, "AUTH_DISABLED", False)
    ws = AsyncMock()
    ws.query_params = {}
    user = await authenticate_websocket(ws, required_role=UserRole.BORROWER)
    assert user is None
    ws.close.assert_awaited_once()
    assert ws.close.call_args[1]["code"] == 4001


@pytest.mark.asyncio
async def test_authenticate_websocket_returns_none_without_closing_when_no_role_required(
    monkeypatch,
):
    """should return None without closing WS when no token and no required_role."""
    monkeypatch.setattr(settings, "AUTH_DISABLED", False)
    ws = AsyncMock()
    ws.query_params = {}
    user = await authenticate_websocket(ws, required_role=None)
    assert user is None
    ws.close.assert_not_awaited()


@pytest.mark.asyncio
async def test_authenticate_websocket_rejects_invalid_token(monkeypatch):
    """should close WS with 4001 when token is malformed or expired."""
    import jwt as pyjwt
    from db.enums import UserRole

    monkeypatch.setattr(settings, "AUTH_DISABLED", False)
    ws = AsyncMock()
    ws.query_params = {"token": "bad-token"}

    with patch(
        "src.routes._chat_handler._decode_token",
        side_effect=pyjwt.InvalidTokenError("bad"),
    ):
        user = await authenticate_websocket(ws, required_role=UserRole.BORROWER)

    assert user is None
    ws.close.assert_awaited_once()
    assert ws.close.call_args[1]["code"] == 4001


@pytest.mark.asyncio
async def test_authenticate_websocket_rejects_wrong_role(monkeypatch):
    """should close WS with 4003 when user has wrong role."""
    from db.enums import UserRole

    from src.schemas.auth import TokenPayload

    monkeypatch.setattr(settings, "AUTH_DISABLED", False)

    fake_payload = TokenPayload(
        sub="user-123",
        email="user@test.com",
        name="Test User",
        realm_access={"roles": ["loan_officer"]},
    )

    ws = AsyncMock()
    ws.query_params = {"token": "fake-jwt"}

    with patch("src.routes._chat_handler._decode_token", return_value=fake_payload):
        user = await authenticate_websocket(ws, required_role=UserRole.BORROWER)

    assert user is None
    ws.close.assert_awaited_once()
    assert ws.close.call_args[1]["code"] == 4003


@pytest.mark.asyncio
async def test_authenticate_websocket_succeeds_with_valid_borrower_token(monkeypatch):
    """should return UserContext when token is valid and role matches."""
    from db.enums import UserRole

    from src.schemas.auth import TokenPayload

    monkeypatch.setattr(settings, "AUTH_DISABLED", False)

    fake_payload = TokenPayload(
        sub="borrower-456",
        email="sarah@example.com",
        name="Sarah Connor",
        realm_access={"roles": ["borrower"]},
    )

    ws = AsyncMock()
    ws.query_params = {"token": "valid-jwt"}

    with patch("src.routes._chat_handler._decode_token", return_value=fake_payload):
        user = await authenticate_websocket(ws, required_role=UserRole.BORROWER)

    assert user is not None
    assert user.user_id == "borrower-456"
    assert user.role == UserRole.BORROWER
    assert user.email == "sarah@example.com"
    assert user.data_scope.own_data_only is True
    ws.close.assert_not_awaited()


# -- Borrower WS endpoint integration --


def test_borrower_ws_endpoint_rejects_invalid_json(client):
    """should return error for non-JSON messages on /api/borrower/chat."""
    with client.websocket_connect("/api/borrower/chat") as ws:
        ws.send_text("not json")
        resp = ws.receive_json()
        assert resp["type"] == "error"
        assert "Invalid JSON" in resp["content"]
