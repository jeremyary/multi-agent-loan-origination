# This project was developed with assistance from AI tools.
"""Tests for application intake service (S-2-F3-01, S-2-F3-02, S-2-F3-03)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.intake import start_application


def _make_user(user_id="borrower-1", role="borrower"):
    """Build a mock UserContext."""
    from db.enums import UserRole

    from src.middleware.auth import _build_data_scope
    from src.schemas.auth import UserContext

    r = UserRole(role)
    return UserContext(
        user_id=user_id,
        role=r,
        email=f"{user_id}@summit-cap.local",
        name=user_id,
        data_scope=_build_data_scope(r, user_id),
    )


def _make_application(app_id=1, stage="application"):
    """Build a mock Application object."""
    from db.enums import ApplicationStage

    app = MagicMock()
    app.id = app_id
    app.stage = ApplicationStage(stage)
    return app


@pytest.mark.asyncio
async def test_start_application_creates_new():
    """When no active application exists, start_application creates one."""
    user = _make_user()
    new_app = _make_application(app_id=42, stage="inquiry")

    session = AsyncMock()

    with (
        patch(
            "src.services.intake.find_active_application",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "src.services.intake.create_application",
            new_callable=AsyncMock,
            return_value=new_app,
        ),
    ):
        result = await start_application(session, user)

    assert result["application_id"] == 42
    assert result["is_new"] is True
    assert result["stage"] == "inquiry"


@pytest.mark.asyncio
async def test_start_application_finds_existing():
    """When an active application exists, start_application returns it."""
    user = _make_user()
    existing_app = _make_application(app_id=10, stage="processing")

    session = AsyncMock()

    with patch(
        "src.services.intake.find_active_application",
        new_callable=AsyncMock,
        return_value=existing_app,
    ):
        result = await start_application(session, user)

    assert result["application_id"] == 10
    assert result["is_new"] is False
    assert result["stage"] == "processing"


@pytest.mark.asyncio
async def test_start_application_tool_creates_new():
    """The start_application tool creates a new app and writes an audit event."""
    from src.agents.borrower_tools import start_application as start_app_tool

    state = {"user_id": "borrower-1", "user_role": "borrower"}
    mock_session = AsyncMock()

    service_result = {
        "application_id": 99,
        "stage": "inquiry",
        "is_new": True,
    }

    with (
        patch("src.agents.borrower_tools.SessionLocal") as mock_sl,
        patch(
            "src.agents.borrower_tools.start_application_service",
            new_callable=AsyncMock,
            return_value=service_result,
        ),
        patch(
            "src.agents.borrower_tools.write_audit_event",
            new_callable=AsyncMock,
        ) as mock_audit,
    ):
        mock_sl.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sl.return_value.__aexit__ = AsyncMock(return_value=False)

        response = await start_app_tool.ainvoke({"state": state})

    assert "99" in response
    assert "Created new application" in response
    mock_audit.assert_called_once()
    audit_kwargs = mock_audit.call_args
    assert audit_kwargs.kwargs["event_type"] == "application_started"
    assert audit_kwargs.kwargs["application_id"] == 99
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_start_application_tool_returns_existing():
    """The start_application tool returns existing app without creating a new one."""
    from src.agents.borrower_tools import start_application as start_app_tool

    state = {"user_id": "borrower-1", "user_role": "borrower"}
    mock_session = AsyncMock()

    service_result = {
        "application_id": 10,
        "stage": "processing",
        "is_new": False,
    }

    with (
        patch("src.agents.borrower_tools.SessionLocal") as mock_sl,
        patch(
            "src.agents.borrower_tools.start_application_service",
            new_callable=AsyncMock,
            return_value=service_result,
        ),
        patch(
            "src.agents.borrower_tools.write_audit_event",
            new_callable=AsyncMock,
        ) as mock_audit,
    ):
        mock_sl.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sl.return_value.__aexit__ = AsyncMock(return_value=False)

        response = await start_app_tool.ainvoke({"state": state})

    assert "10" in response
    assert "already have an active application" in response
    mock_audit.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_update_tool_formats_success():
    """The update_application_data tool formats updated + remaining fields."""
    from src.agents.borrower_tools import update_application_data

    state = {"user_id": "borrower-1", "user_role": "borrower"}
    mock_session = AsyncMock()

    service_result = {
        "updated": ["gross_monthly_income", "employment_status"],
        "errors": {},
        "remaining": ["ssn", "date_of_birth"],
        "corrections": {},
    }

    with (
        patch("src.agents.borrower_tools.SessionLocal") as mock_sl,
        patch(
            "src.agents.borrower_tools.update_application_fields",
            new_callable=AsyncMock,
            return_value=service_result,
        ),
        patch("src.agents.borrower_tools.write_audit_event", new_callable=AsyncMock),
    ):
        mock_sl.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sl.return_value.__aexit__ = AsyncMock(return_value=False)

        response = await update_application_data.ainvoke(
            {
                "application_id": 42,
                "fields": '{"gross_monthly_income": "6250", "employment_status": "w2"}',
                "state": state,
            }
        )

    assert "gross_monthly_income" in response
    assert "employment_status" in response
    assert "Still needed" in response
    assert "ssn" in response


@pytest.mark.asyncio
async def test_update_tool_formats_validation_errors():
    """The update_application_data tool reports validation errors per field."""
    from src.agents.borrower_tools import update_application_data

    state = {"user_id": "borrower-1", "user_role": "borrower"}
    mock_session = AsyncMock()

    service_result = {
        "updated": ["email"],
        "errors": {"ssn": "SSN must be 9 digits (XXX-XX-XXXX)"},
        "remaining": ["ssn"],
        "corrections": {},
    }

    with (
        patch("src.agents.borrower_tools.SessionLocal") as mock_sl,
        patch(
            "src.agents.borrower_tools.update_application_fields",
            new_callable=AsyncMock,
            return_value=service_result,
        ),
        patch("src.agents.borrower_tools.write_audit_event", new_callable=AsyncMock),
    ):
        mock_sl.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sl.return_value.__aexit__ = AsyncMock(return_value=False)

        response = await update_application_data.ainvoke(
            {
                "application_id": 42,
                "fields": '{"email": "test@example.com", "ssn": "123"}',
                "state": state,
            }
        )

    assert "email" in response
    assert "Could not save ssn" in response
    assert "9 digits" in response


@pytest.mark.asyncio
async def test_update_tool_rejects_bad_json():
    """The update_application_data tool handles unparseable JSON input."""
    from src.agents.borrower_tools import update_application_data

    state = {"user_id": "borrower-1", "user_role": "borrower"}

    response = await update_application_data.ainvoke(
        {"application_id": 42, "fields": "not json at all", "state": state}
    )

    assert "Could not parse" in response


@pytest.mark.asyncio
async def test_update_tool_all_fields_complete():
    """When all fields are filled, the tool reports completion."""
    from src.agents.borrower_tools import update_application_data

    state = {"user_id": "borrower-1", "user_role": "borrower"}
    mock_session = AsyncMock()

    service_result = {
        "updated": ["credit_score"],
        "errors": {},
        "remaining": [],
        "corrections": {},
    }

    with (
        patch("src.agents.borrower_tools.SessionLocal") as mock_sl,
        patch(
            "src.agents.borrower_tools.update_application_fields",
            new_callable=AsyncMock,
            return_value=service_result,
        ),
        patch("src.agents.borrower_tools.write_audit_event", new_callable=AsyncMock),
    ):
        mock_sl.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sl.return_value.__aexit__ = AsyncMock(return_value=False)

        response = await update_application_data.ainvoke(
            {"application_id": 42, "fields": '{"credit_score": "750"}', "state": state}
        )

    assert "All required fields are complete" in response
