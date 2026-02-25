# This project was developed with assistance from AI tools.
"""Co-borrower management via API endpoints with real FK/unique constraints."""

import pytest

pytestmark = pytest.mark.integration


async def test_add_coborrower(client_factory, seed_data):
    """POST /applications/{id}/borrowers -> 201, response has both borrowers."""
    from tests.functional.personas import loan_officer

    client = await client_factory(loan_officer())
    resp = await client.post(
        f"/api/applications/{seed_data.michael_app.id}/borrowers",
        json={"borrower_id": seed_data.jennifer.id, "is_primary": False},
    )
    assert resp.status_code == 201
    borrowers = resp.json()["borrowers"]
    assert len(borrowers) == 2
    ids = {b["id"] for b in borrowers}
    assert seed_data.michael.id in ids
    assert seed_data.jennifer.id in ids
    await client.aclose()


async def test_add_duplicate_returns_409(client_factory, seed_data):
    """Same borrower twice -> 409."""
    from tests.functional.personas import loan_officer

    # Jennifer is already co-borrower on sarah_app1 (from seed_data)
    client = await client_factory(loan_officer())
    resp = await client.post(
        f"/api/applications/{seed_data.sarah_app1.id}/borrowers",
        json={"borrower_id": seed_data.jennifer.id, "is_primary": False},
    )
    assert resp.status_code == 409
    await client.aclose()


async def test_add_nonexistent_borrower_returns_404(client_factory, seed_data):
    """borrower_id=99999 -> 404."""
    from tests.functional.personas import loan_officer

    client = await client_factory(loan_officer())
    resp = await client.post(
        f"/api/applications/{seed_data.sarah_app1.id}/borrowers",
        json={"borrower_id": 99999, "is_primary": False},
    )
    assert resp.status_code == 404
    await client.aclose()


async def test_remove_coborrower(client_factory, seed_data):
    """DELETE non-primary borrower -> success."""
    from tests.functional.personas import loan_officer

    client = await client_factory(loan_officer())
    resp = await client.delete(
        f"/api/applications/{seed_data.sarah_app1.id}/borrowers/{seed_data.jennifer.id}",
    )
    assert resp.status_code == 200
    borrowers = resp.json()["borrowers"]
    assert len(borrowers) == 1
    assert borrowers[0]["first_name"] == "Sarah"
    await client.aclose()


async def test_remove_primary_returns_400(client_factory, seed_data):
    """DELETE primary borrower -> 400."""
    from tests.functional.personas import loan_officer

    client = await client_factory(loan_officer())
    resp = await client.delete(
        f"/api/applications/{seed_data.sarah_app1.id}/borrowers/{seed_data.sarah.id}",
    )
    assert resp.status_code == 400
    await client.aclose()


async def test_remove_last_borrower_returns_400(client_factory, seed_data):
    """Remove sole borrower -> 400 (michael_app has only michael)."""
    from tests.functional.personas import loan_officer

    client = await client_factory(loan_officer())
    resp = await client.delete(
        f"/api/applications/{seed_data.michael_app.id}/borrowers/{seed_data.michael.id}",
    )
    assert resp.status_code == 400
    await client.aclose()


async def test_coborrower_in_application_response(client_factory, seed_data):
    """GET shows all borrowers with correct is_primary."""
    from tests.functional.personas import admin

    client = await client_factory(admin())
    resp = await client.get(f"/api/applications/{seed_data.sarah_app1.id}")
    assert resp.status_code == 200
    borrowers = resp.json()["borrowers"]
    assert len(borrowers) == 2
    primary = [b for b in borrowers if b["is_primary"]]
    assert len(primary) == 1
    assert primary[0]["first_name"] == "Sarah"
    await client.aclose()


async def test_borrower_cannot_manage_coborrowers(client_factory, seed_data):
    """Borrower role -> 403 on co-borrower management."""
    from tests.functional.personas import borrower_sarah

    client = await client_factory(borrower_sarah())
    resp = await client.post(
        f"/api/applications/{seed_data.sarah_app1.id}/borrowers",
        json={"borrower_id": seed_data.michael.id, "is_primary": False},
    )
    assert resp.status_code == 403
    await client.aclose()
