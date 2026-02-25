# This project was developed with assistance from AI tools.
"""Fixtures for functional tests.

The real app from ``src.main`` is a module singleton. ``_clean_overrides``
ensures dependency_overrides are cleared after every test so persona
configuration from one test never leaks into the next.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app as real_app
from src.schemas.auth import UserContext

from .mock_db import configure_app_for_persona


@pytest.fixture(autouse=True)
def _clean_overrides():
    """Clear app dependency overrides after each test."""
    yield
    real_app.dependency_overrides.clear()


@pytest.fixture
def app():
    """Return the real FastAPI app with all routers mounted."""
    return real_app


@pytest.fixture
def make_client(app):
    """Factory fixture: configure persona + mock DB, return TestClient."""

    def _make(user: UserContext, session: AsyncMock) -> TestClient:
        configure_app_for_persona(app, user, session)
        return TestClient(app)

    return _make


@pytest.fixture
def make_upload_client(app):
    """Factory fixture: configure persona + mock DB + mock storage for uploads.

    Returns (TestClient, mock_storage). The storage patch is automatically
    stopped after each test via _clean_overrides.
    """
    patchers = []

    def _make(user: UserContext, session: AsyncMock) -> tuple[TestClient, MagicMock]:
        configure_app_for_persona(app, user, session)

        mock_storage = MagicMock()
        mock_storage.build_object_key.return_value = "101/501/test.pdf"
        mock_storage.upload_file = AsyncMock(return_value="101/501/test.pdf")

        patcher = patch("src.services.document.get_storage_service", return_value=mock_storage)
        patcher.start()
        patchers.append(patcher)

        return TestClient(app), mock_storage

    yield _make

    for p in patchers:
        p.stop()
