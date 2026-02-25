# This project was developed with assistance from AI tools.
"""Health check against real PostgreSQL."""

import pytest

pytestmark = pytest.mark.integration


async def test_health_returns_api_and_db(client_factory):
    """GET /health/ returns 200 with 2 items, both healthy."""
    from tests.functional.personas import admin

    client = await client_factory(admin())
    resp = await client.get("/health/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(item["status"] == "healthy" for item in data)
    await client.aclose()


async def test_health_db_shows_postgres(client_factory):
    """DB health message mentions PostgreSQL."""
    from tests.functional.personas import admin

    client = await client_factory(admin())
    resp = await client.get("/health/")
    data = resp.json()
    db_item = next(item for item in data if item["name"] == "Database")
    assert "PostgreSQL" in db_item["message"]
    await client.aclose()


async def test_health_includes_version(client_factory):
    """API item has a version field."""
    from src import __version__
    from tests.functional.personas import admin

    client = await client_factory(admin())
    resp = await client.get("/health/")
    data = resp.json()
    api_item = next(item for item in data if item["name"] == "API")
    assert api_item["version"] == __version__
    await client.aclose()
