"""
Pytest configuration and fixtures
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """FastAPI test client fixture"""
    return TestClient(app)


@pytest.fixture
def health_response(client):
    """Get health check response data"""
    response = client.get("/health/")
    assert response.status_code == 200
    return response.json()
