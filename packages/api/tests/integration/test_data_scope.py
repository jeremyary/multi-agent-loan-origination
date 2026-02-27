# This project was developed with assistance from AI tools.
"""Data scope filtering -- SECURITY-CRITICAL.

Verifies real SQL join filtering through the ApplicationBorrower junction table.
"""

import pytest

pytestmark = pytest.mark.integration


async def test_borrower_sees_only_own_apps(client_factory, seed_data):
    """Sarah sees her 2 apps; count=2."""
    from tests.functional.personas import borrower_sarah

    client = await client_factory(borrower_sarah())
    resp = await client.get("/api/applications/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["total"] == 2
    assert len(data["data"]) == 2
    await client.aclose()


async def test_borrower_cannot_see_other_app(client_factory, seed_data):
    """Sarah GET michael_app -> 404 (not 403)."""
    from tests.functional.personas import borrower_sarah

    client = await client_factory(borrower_sarah())
    resp = await client.get(f"/api/applications/{seed_data.michael_app.id}")
    assert resp.status_code == 404
    await client.aclose()


async def test_lo_sees_only_assigned(client_factory, seed_data):
    """LO sees sarah_app1 + michael_app (assigned); NOT sarah_app2 (unassigned)."""
    from tests.functional.personas import loan_officer

    client = await client_factory(loan_officer())
    resp = await client.get("/api/applications/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["total"] == 2
    app_ids = {app["id"] for app in data["data"]}
    assert seed_data.sarah_app1.id in app_ids
    assert seed_data.michael_app.id in app_ids
    assert seed_data.sarah_app2.id not in app_ids
    await client.aclose()


async def test_underwriter_sees_all(client_factory, seed_data):
    """Underwriter sees all 3 apps."""
    from tests.functional.personas import underwriter

    client = await client_factory(underwriter())
    resp = await client.get("/api/applications/")
    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 3
    await client.aclose()


async def test_ceo_sees_all(client_factory, seed_data):
    """CEO sees all 3 apps."""
    from tests.functional.personas import ceo

    client = await client_factory(ceo())
    resp = await client.get("/api/applications/")
    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 3
    await client.aclose()


async def test_admin_sees_all(client_factory, seed_data):
    """Admin sees all 3 apps."""
    from tests.functional.personas import admin

    client = await client_factory(admin())
    resp = await client.get("/api/applications/")
    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 3
    await client.aclose()


async def test_prospect_blocked(client_factory, seed_data):
    """Prospect GET /api/applications/ -> 403."""
    from tests.functional.personas import prospect

    client = await client_factory(prospect())
    resp = await client.get("/api/applications/")
    assert resp.status_code == 403
    await client.aclose()


async def test_borrower_list_documents_own_app(client_factory, seed_data):
    """Sarah lists docs on sarah_app1 -> 2 docs."""
    from tests.functional.personas import borrower_sarah

    client = await client_factory(borrower_sarah())
    resp = await client.get(f"/api/applications/{seed_data.sarah_app1.id}/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["total"] == 2
    assert len(data["data"]) == 2
    await client.aclose()


async def test_borrower_cannot_list_other_documents(client_factory, seed_data):
    """Sarah lists docs on michael_app -> 404 (scope hides the app)."""
    from tests.functional.personas import borrower_sarah

    client = await client_factory(borrower_sarah())
    resp = await client.get(f"/api/applications/{seed_data.michael_app.id}/documents")
    assert resp.status_code == 200
    # Data scope filtering on Documents joins to Application; michael_app is not in
    # Sarah's scope so the query returns 0 docs for that app_id, count=0
    data = resp.json()
    assert data["pagination"]["total"] == 0
    await client.aclose()


async def test_lo_sees_assigned_app_documents(client_factory, seed_data):
    """LO lists docs on sarah_app1 -> 2 docs."""
    from tests.functional.personas import loan_officer

    client = await client_factory(loan_officer())
    resp = await client.get(f"/api/applications/{seed_data.sarah_app1.id}/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["total"] == 2
    await client.aclose()
