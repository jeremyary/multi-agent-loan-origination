# This project was developed with assistance from AI tools.
"""Mock database utilities for functional tests.

Provides an AsyncMock session that handles the three result patterns used by
the service layer:
  1. ``.scalar()`` -- count queries
  2. ``.unique().scalars().all()`` -- list queries
  3. ``.unique().scalar_one_or_none()`` -- single-item queries
"""

from unittest.mock import AsyncMock, MagicMock

from db import get_compliance_db, get_db

from src.middleware.auth import get_current_user
from src.schemas.auth import UserContext


def make_mock_session(
    items: list | None = None,
    single: object | None = None,
    count: int | None = None,
) -> AsyncMock:
    """Build an AsyncMock session that returns predictable query results.

    Args:
        items: List of ORM objects for ``.unique().scalars().all()``.
        single: Single ORM object for ``.unique().scalar_one_or_none()``.
        count: Integer for ``.scalar()`` (count queries).

    When only ``items`` is provided, count and single are inferred:
    - count = len(items)
    - single = items[0] if items else None
    """
    if items is not None and count is None:
        count = len(items)
    if items is not None and single is None:
        single = items[0] if items else None

    session = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar.return_value = count or 0
    mock_result.unique.return_value.scalars.return_value.all.return_value = items or []
    mock_result.unique.return_value.scalar_one_or_none.return_value = single

    session.execute = AsyncMock(return_value=mock_result)
    return session


def configure_app_for_persona(app, user: UserContext, session: AsyncMock) -> None:
    """Override get_current_user, get_db, and get_compliance_db on the real app."""

    async def fake_user():
        return user

    async def fake_db():
        yield session

    async def fake_compliance_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_compliance_db] = fake_compliance_db
