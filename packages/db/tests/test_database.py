"""
Database tests
"""

import pytest
from src.database import engine


@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection"""
    async with engine.begin() as conn:
        result = await conn.execute("SELECT 1")
        assert result.scalar() == 1
