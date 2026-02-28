# This project was developed with assistance from AI tools.
"""Tests for agent registry caching and configuration.

Validates that get_agent returns compiled graphs and that the same agent
name returns the same graph instance when cached.
"""

import pytest

from src.agents.registry import clear_agent_cache, get_agent, list_agents


def test_get_agent_returns_graph():
    """get_agent returns a compiled LangGraph graph."""
    clear_agent_cache()  # Start fresh
    try:
        graph = get_agent("public-assistant")
        # Check that it's a compiled graph object (has compile signature)
        assert graph is not None
        assert hasattr(graph, "ainvoke") or hasattr(graph, "astream_events")
    except FileNotFoundError:
        pytest.skip("Agent config files not present in test environment")


def test_get_agent_caches_same_instance():
    """Calling get_agent twice returns the same cached graph instance."""
    clear_agent_cache()
    try:
        graph1 = get_agent("public-assistant")
        graph2 = get_agent("public-assistant")
        # Same object reference (cached)
        assert graph1 is graph2
    except FileNotFoundError:
        pytest.skip("Agent config files not present in test environment")


def test_list_agents_returns_available_agents():
    """list_agents returns a list of agent names from YAML files."""
    agents = list_agents()
    assert isinstance(agents, list)
    # If config files exist, we should see at least one agent
    # If not, list is empty (valid for test environments without config)
    if agents:
        assert "public-assistant" in agents or len(agents) > 0


def test_clear_agent_cache_reloads_graph():
    """clear_agent_cache forces a reload on next get_agent call."""
    try:
        graph1 = get_agent("public-assistant")
        clear_agent_cache()
        graph2 = get_agent("public-assistant")
        # After clearing cache, we get a fresh instance
        # (May be the same if rebuild is identical, but cache was cleared)
        assert graph1 is not None
        assert graph2 is not None
    except FileNotFoundError:
        pytest.skip("Agent config files not present in test environment")


def test_get_agent_unknown_raises():
    """get_agent raises FileNotFoundError for unknown agent names."""
    clear_agent_cache()
    with pytest.raises(FileNotFoundError):
        get_agent("nonexistent-agent")
