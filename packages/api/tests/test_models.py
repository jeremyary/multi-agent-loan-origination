# This project was developed with assistance from AI tools.
"""
Domain model structure tests
"""


def test_application_relationships():
    """Application model should have all expected ORM relationships wired."""
    from db import Application

    rel_names = {r.key for r in Application.__mapper__.relationships}
    assert "application_borrowers" in rel_names
    assert "financials" in rel_names
    assert "rate_locks" in rel_names
    assert "conditions" in rel_names
    assert "decisions" in rel_names
    assert "documents" in rel_names
