# This project was developed with assistance from AI tools.
"""Unit tests for ConversationService -- thread ID generation, ownership, URL derivation."""

import pytest

from src.services.conversation import ConversationService, derive_psycopg_url


class TestGetThreadId:
    """Tests for ConversationService.get_thread_id()."""

    def test_deterministic(self):
        """should return the same thread_id for the same user_id."""
        tid1 = ConversationService.get_thread_id("sarah-001")
        tid2 = ConversationService.get_thread_id("sarah-001")
        assert tid1 == tid2

    def test_different_users(self):
        """should return different thread_ids for different user_ids."""
        tid1 = ConversationService.get_thread_id("sarah-001")
        tid2 = ConversationService.get_thread_id("james-002")
        assert tid1 != tid2

    def test_format(self):
        """should produce user:{id}:agent:{name} format."""
        tid = ConversationService.get_thread_id("sarah-001", "public-assistant")
        assert tid == "user:sarah-001:agent:public-assistant"

    def test_different_agents(self):
        """should produce different thread_ids for different agent_names."""
        tid1 = ConversationService.get_thread_id("sarah-001", "public-assistant")
        tid2 = ConversationService.get_thread_id("sarah-001", "borrower-assistant")
        assert tid1 != tid2

    def test_default_agent(self):
        """should default to public-assistant agent."""
        tid = ConversationService.get_thread_id("sarah-001")
        assert tid == "user:sarah-001:agent:public-assistant"


class TestVerifyThreadOwnership:
    """Tests for ConversationService.verify_thread_ownership()."""

    def test_match(self):
        """should not raise for correct user."""
        tid = "user:sarah-001:agent:public-assistant"
        ConversationService.verify_thread_ownership(tid, "sarah-001")

    def test_mismatch(self):
        """should raise PermissionError for wrong user."""
        tid = "user:sarah-001:agent:public-assistant"
        with pytest.raises(PermissionError, match="does not belong"):
            ConversationService.verify_thread_ownership(tid, "james-002")

    def test_admin_no_override(self):
        """should reject admin user_id accessing borrower thread (S-2-F19-04)."""
        tid = "user:sarah-001:agent:borrower-assistant"
        with pytest.raises(PermissionError):
            ConversationService.verify_thread_ownership(tid, "admin-001")


class TestDerivePsycopgUrl:
    """Tests for derive_psycopg_url()."""

    def test_strips_asyncpg(self):
        """should strip +asyncpg from DATABASE_URL."""
        url = "postgresql+asyncpg://user:pass@localhost:5433/summit-cap"
        assert derive_psycopg_url(url) == "postgresql://user:pass@localhost:5433/summit-cap"

    def test_already_plain(self):
        """should handle URL without driver prefix."""
        url = "postgresql://user:pass@localhost:5433/summit-cap"
        assert derive_psycopg_url(url) == "postgresql://user:pass@localhost:5433/summit-cap"
