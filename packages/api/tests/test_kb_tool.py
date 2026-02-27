# This project was developed with assistance from AI tools.
"""Tests for the kb_search agent tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.compliance_tools import kb_search
from src.services.compliance.knowledge_base.search import KBSearchResult


def _make_result(
    chunk_text: str,
    tier: int,
    source: str = "Test Doc",
    section: str | None = "Test Section",
    effective_date: str | None = "2024-01-01",
) -> KBSearchResult:
    """Create a KBSearchResult for testing."""
    tier_labels = {1: "Federal Regulation", 2: "Agency Guideline", 3: "Internal Policy"}
    return KBSearchResult(
        chunk_text=chunk_text,
        source_document=source,
        section_ref=section,
        tier=tier,
        tier_label=tier_labels.get(tier, f"Tier {tier}"),
        similarity=0.8,
        boosted_similarity=0.8,
        effective_date=effective_date,
    )


@pytest.fixture
def agent_state():
    """Minimal agent state dict for tool calls."""
    return {
        "user_id": "lo-test-001",
        "user_role": "loan_officer",
        "session_id": "test-session-123",
    }


@pytest.fixture
def mock_session_factory():
    """Create a mock SessionLocal context manager."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    return mock_ctx, mock_session


class TestKbSearchTool:
    """Tests for the kb_search tool function."""

    @pytest.mark.asyncio
    async def test_formats_results_with_citations(self, agent_state, mock_session_factory):
        """Output includes tier label, source, section, and text."""
        mock_ctx, mock_session = mock_session_factory
        results = [
            _make_result(
                "The QM safe harbor requires DTI not exceed 43%",
                tier=1,
                source="12 CFR 1026.43",
                section="QM Safe Harbor",
                effective_date="2014-01-10",
            ),
        ]

        with (
            patch("src.agents.compliance_tools.SessionLocal", return_value=mock_ctx),
            patch(
                "src.agents.compliance_tools.search_kb",
                new_callable=AsyncMock,
                return_value=results,
            ),
            patch("src.agents.compliance_tools.detect_conflicts", return_value=[]),
            patch("src.agents.compliance_tools.write_audit_event", new_callable=AsyncMock),
        ):
            output = await kb_search.ainvoke({"query": "DTI requirements", "state": agent_state})

        assert "[Federal Regulation]" in output
        assert "12 CFR 1026.43" in output
        assert "QM Safe Harbor" in output
        assert "2014-01-10" in output
        assert "43%" in output

    @pytest.mark.asyncio
    async def test_no_results_returns_rephrase(self, agent_state, mock_session_factory):
        """Empty results return a 'rephrase' message."""
        mock_ctx, mock_session = mock_session_factory

        with (
            patch("src.agents.compliance_tools.SessionLocal", return_value=mock_ctx),
            patch("src.agents.compliance_tools.search_kb", new_callable=AsyncMock, return_value=[]),
            patch("src.agents.compliance_tools.write_audit_event", new_callable=AsyncMock),
        ):
            output = await kb_search.ainvoke({"query": "something obscure", "state": agent_state})

        assert "rephrase" in output.lower() or "no relevant" in output.lower()

    @pytest.mark.asyncio
    async def test_writes_audit_event(self, agent_state, mock_session_factory):
        """Tool call writes an audit event with tool name and query."""
        mock_ctx, mock_session = mock_session_factory
        mock_audit = AsyncMock()

        with (
            patch("src.agents.compliance_tools.SessionLocal", return_value=mock_ctx),
            patch("src.agents.compliance_tools.search_kb", new_callable=AsyncMock, return_value=[]),
            patch("src.agents.compliance_tools.write_audit_event", mock_audit),
        ):
            await kb_search.ainvoke({"query": "DTI limits", "state": agent_state})

        mock_audit.assert_called()
        call_kwargs = mock_audit.call_args_list[0]
        event_data = call_kwargs.kwargs.get("event_data") or call_kwargs[1].get("event_data")
        assert event_data["tool"] == "kb_search"
        assert event_data["query"] == "DTI limits"

    @pytest.mark.asyncio
    async def test_includes_regulatory_disclaimer(self, agent_state, mock_session_factory):
        """Output always includes regulatory disclaimer."""
        mock_ctx, mock_session = mock_session_factory
        results = [_make_result("Some regulatory text", tier=1)]

        with (
            patch("src.agents.compliance_tools.SessionLocal", return_value=mock_ctx),
            patch(
                "src.agents.compliance_tools.search_kb",
                new_callable=AsyncMock,
                return_value=results,
            ),
            patch("src.agents.compliance_tools.detect_conflicts", return_value=[]),
            patch("src.agents.compliance_tools.write_audit_event", new_callable=AsyncMock),
        ):
            output = await kb_search.ainvoke({"query": "any query", "state": agent_state})

        assert "simulated for demonstration purposes" in output

    @pytest.mark.asyncio
    async def test_conflict_section_in_output(self, agent_state, mock_session_factory):
        """When conflicts detected, output includes CONFLICTS DETECTED section."""
        mock_ctx, mock_session = mock_session_factory
        results = [
            _make_result("DTI max 43%", tier=1),
            _make_result("DTI max 40%", tier=3),
        ]

        from src.services.compliance.knowledge_base.conflict import Conflict

        conflicts = [
            Conflict(
                result_a=results[0],
                result_b=results[1],
                conflict_type="numeric_threshold",
                description="Federal cites 43% while Internal cites 40%",
            )
        ]

        with (
            patch("src.agents.compliance_tools.SessionLocal", return_value=mock_ctx),
            patch(
                "src.agents.compliance_tools.search_kb",
                new_callable=AsyncMock,
                return_value=results,
            ),
            patch("src.agents.compliance_tools.detect_conflicts", return_value=conflicts),
            patch("src.agents.compliance_tools.write_audit_event", new_callable=AsyncMock),
        ):
            output = await kb_search.ainvoke({"query": "DTI limits", "state": agent_state})

        assert "CONFLICTS DETECTED" in output
        assert "Numeric Threshold" in output
        assert "43%" in output
        assert "40%" in output
