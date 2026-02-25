# This project was developed with assistance from AI tools.
"""Pagination count queries and join inflation tests."""

import pytest

pytestmark = pytest.mark.integration


async def test_count_matches_data_length(client_factory, seed_data):
    """count == len(data) for each role."""
    from tests.functional.personas import admin, borrower_sarah, loan_officer

    for persona_fn in [admin, borrower_sarah, loan_officer]:
        client = await client_factory(persona_fn())
        resp = await client.get("/api/applications/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == len(data["data"]), (
            f"Mismatch for {persona_fn.__name__}: count={data['count']} len={len(data['data'])}"
        )
        await client.aclose()


async def test_offset_limit(client_factory, seed_data):
    """?offset=1&limit=1 returns 1 item, correct total count."""
    from tests.functional.personas import admin

    client = await client_factory(admin())
    resp = await client.get("/api/applications/", params={"offset": 1, "limit": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
    assert data["count"] == 3  # Total count is still 3
    await client.aclose()


async def test_coborrower_no_count_inflation(client_factory, seed_data):
    """App with 2 borrowers counts as 1 (not inflated by join)."""
    from tests.functional.personas import admin

    # sarah_app1 has 2 borrowers (Sarah + Jennifer). Count should still be 3 total.
    client = await client_factory(admin())
    resp = await client.get("/api/applications/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    await client.aclose()


async def test_limit_exceeding_total(client_factory, seed_data):
    """?limit=100 returns all, correct count."""
    from tests.functional.personas import admin

    client = await client_factory(admin())
    resp = await client.get("/api/applications/", params={"limit": 100})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    assert len(data["data"]) == 3
    await client.aclose()


async def test_zero_results(client_factory, seed_data):
    """Borrower with no apps -> count=0, data=[]."""
    from db.enums import UserRole

    from src.schemas.auth import DataScope, UserContext

    # Jennifer is only a co-borrower (not primary on any app owned solo)
    # But she IS linked via junction on sarah_app1 -- she'll see 1 app
    # Use a completely unknown user with no apps
    nobody = UserContext(
        user_id="nobody-000",
        role=UserRole.BORROWER,
        email="nobody@example.com",
        name="Nobody",
        data_scope=DataScope(own_data_only=True, user_id="nobody-000"),
    )
    client = await client_factory(nobody)
    resp = await client.get("/api/applications/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["data"] == []
    await client.aclose()
