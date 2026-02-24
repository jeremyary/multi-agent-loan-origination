# This project was developed with assistance from AI tools.
"""Fixtures for functional tests.

The real app from ``src.main`` is a module singleton. ``_clean_overrides``
ensures dependency_overrides are cleared after every test so persona
configuration from one test never leaks into the next.
"""

from unittest.mock import AsyncMock

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
