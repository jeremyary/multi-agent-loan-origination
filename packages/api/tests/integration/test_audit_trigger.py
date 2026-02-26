# This project was developed with assistance from AI tools.
"""Audit append-only trigger enforcement (S-2-F15-02, F15-03).

Verifies the PostgreSQL BEFORE trigger blocks UPDATE and DELETE on
audit_events while allowing INSERT (append-only guarantee).  These tests
run against real PostgreSQL via testcontainers.
"""

import pytest
import pytest_asyncio
from sqlalchemy import text

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def audit_cleanup(async_engine):
    """Truncate audit tables after each test (TRUNCATE bypasses row triggers)."""
    yield
    async with async_engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE audit_violations, audit_events CASCADE"))


async def test_audit_insert_allowed(async_engine, audit_cleanup):
    """INSERT into audit_events succeeds (append-only allows appends)."""
    async with async_engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO audit_events (event_type, user_id) "
                "VALUES ('insert_test', 'test-user') RETURNING id"
            )
        )
        assert result.scalar() is not None


async def test_audit_update_blocked(async_engine, audit_cleanup):
    """UPDATE on audit_events is blocked by trigger."""
    async with async_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO audit_events (event_type, user_id) "
                "VALUES ('update_block_test', 'test-user')"
            )
        )

    async with async_engine.connect() as conn:
        txn = await conn.begin()
        with pytest.raises(Exception, match="append-only"):
            await conn.execute(
                text(
                    "UPDATE audit_events SET event_type = 'tampered' "
                    "WHERE event_type = 'update_block_test'"
                )
            )
        await txn.rollback()

    # Original row unchanged
    async with async_engine.begin() as conn:
        result = await conn.execute(
            text("SELECT event_type FROM audit_events WHERE event_type = 'update_block_test'")
        )
        assert result.scalar() == "update_block_test"


async def test_audit_delete_blocked(async_engine, audit_cleanup):
    """DELETE on audit_events is blocked by trigger."""
    async with async_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO audit_events (event_type, user_id) "
                "VALUES ('delete_block_test', 'test-user')"
            )
        )

    async with async_engine.connect() as conn:
        txn = await conn.begin()
        with pytest.raises(Exception, match="append-only"):
            await conn.execute(
                text("DELETE FROM audit_events WHERE event_type = 'delete_block_test'")
            )
        await txn.rollback()

    # Row still exists
    async with async_engine.begin() as conn:
        result = await conn.execute(
            text("SELECT count(*) FROM audit_events WHERE event_type = 'delete_block_test'")
        )
        assert result.scalar() == 1


async def test_audit_violations_table_exists(async_engine):
    """audit_violations table was created by migration."""
    async with async_engine.begin() as conn:
        result = await conn.execute(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_name = 'audit_violations' AND table_schema = 'public'"
            )
        )
        assert result.scalar() == 1


async def test_trigger_error_includes_operation_type(async_engine, audit_cleanup):
    """Trigger error message identifies the attempted operation (UPDATE/DELETE)."""
    async with async_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO audit_events (event_type, user_id) "
                "VALUES ('op_type_test', 'test-user')"
            )
        )

    # UPDATE error mentions UPDATE
    async with async_engine.connect() as conn:
        txn = await conn.begin()
        with pytest.raises(Exception, match="UPDATE"):
            await conn.execute(
                text("UPDATE audit_events SET event_type = 'x' WHERE event_type = 'op_type_test'")
            )
        await txn.rollback()

    # DELETE error mentions DELETE
    async with async_engine.connect() as conn:
        txn = await conn.begin()
        with pytest.raises(Exception, match="DELETE"):
            await conn.execute(text("DELETE FROM audit_events WHERE event_type = 'op_type_test'"))
        await txn.rollback()
