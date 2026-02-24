# This project was developed with assistance from AI tools.
"""Tests for agent tools, registry, and WebSocket chat endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.agents.registry import list_agents, load_agent_config
from src.agents.tools import affordability_calc, product_info
from src.core.config import settings
from src.main import app


@pytest.fixture(autouse=True)
def _disable_auth(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_DISABLED", True)


@pytest.fixture
def client():
    return TestClient(app)


# -- Tools --


def test_product_info_tool_returns_all_products():
    """product_info tool should return all 6 mortgage products."""
    result = product_info.invoke({})
    assert "30-Year Fixed Conventional" in result
    assert "FHA Loan" in result
    assert "VA Loan" in result
    # Should have 6 products (6 bullet points)
    assert result.count("- **") == 6


def test_affordability_calc_tool_returns_estimate():
    """affordability_calc tool should return formatted estimate."""
    result = affordability_calc.invoke(
        {"gross_annual_income": 80000, "monthly_debts": 500, "down_payment": 20000}
    )
    assert "Max loan amount:" in result
    assert "Estimated monthly payment:" in result
    assert "DTI ratio:" in result


# -- Registry --


def test_list_agents_finds_public_assistant():
    """Agent registry should discover public-assistant from config dir."""
    agents = list_agents()
    assert "public-assistant" in agents


def test_load_agent_config_has_required_fields():
    """Agent config should have name, persona, and system_prompt."""
    config = load_agent_config("public-assistant")
    assert config["agent"]["name"] == "public_assistant"
    assert config["agent"]["persona"] == "prospect"
    assert "system_prompt" in config
    assert len(config["system_prompt"]) > 50


# -- WebSocket --


def test_websocket_rejects_invalid_json(client):
    """WebSocket should return error for non-JSON messages."""
    with client.websocket_connect("/api/chat") as ws:
        ws.send_text("not json")
        resp = ws.receive_json()
        assert resp["type"] == "error"
        assert "Invalid JSON" in resp["content"]


def test_websocket_rejects_missing_content(client):
    """WebSocket should return error for messages without content."""
    with client.websocket_connect("/api/chat") as ws:
        ws.send_json({"type": "message"})
        resp = ws.receive_json()
        assert resp["type"] == "error"


def test_existing_public_endpoint_still_works(client):
    """Refactoring affordability calc into services shouldn't break the route."""
    response = client.post(
        "/api/public/calculate-affordability",
        json={"gross_annual_income": 80000, "monthly_debts": 500, "down_payment": 20000},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["max_loan_amount"] > 0


# -- Safety shield graph integration --


@pytest.fixture
def _fresh_graph():
    """Clear the agent registry graph cache before and after each test."""
    from src.agents.registry import _graphs

    _graphs.clear()
    yield
    _graphs.clear()


@pytest.mark.asyncio
async def test_input_shield_blocks_unsafe_message(_fresh_graph, monkeypatch):
    """should short-circuit to END with refusal when input is flagged unsafe."""
    from unittest.mock import AsyncMock

    from langchain_core.messages import HumanMessage

    from src.agents.base import SAFETY_REFUSAL_MESSAGE
    from src.inference.safety import SafetyChecker, SafetyResult

    mock_checker = AsyncMock(spec=SafetyChecker)
    mock_checker.check_input.return_value = SafetyResult(is_safe=False, violation_categories=["S1"])
    monkeypatch.setattr("src.agents.base.get_safety_checker", lambda: mock_checker)

    from src.agents.registry import get_agent

    graph = get_agent("public-assistant")
    result = await graph.ainvoke({"messages": [HumanMessage(content="harmful request")]})

    assert result.get("safety_blocked") is True
    assert result["messages"][-1].content == SAFETY_REFUSAL_MESSAGE
    mock_checker.check_input.assert_awaited_once()
    mock_checker.check_output.assert_not_awaited()


@pytest.mark.asyncio
async def test_input_shield_passes_when_disabled(_fresh_graph, monkeypatch):
    """should not block when shields are disabled (get_safety_checker returns None).

    Verifies that safety_blocked is NOT set, even though the downstream LLM call
    will fail (no real model in test env). The exception from classify/agent is
    expected -- the assertion is that input_shield didn't cause it.
    """
    monkeypatch.setattr("src.agents.base.get_safety_checker", lambda: None)

    from langchain_core.messages import HumanMessage

    from src.agents.registry import get_agent

    graph = get_agent("public-assistant")
    try:
        result = await graph.ainvoke({"messages": [HumanMessage(content="Hello")]})
        # If we somehow get a result, safety_blocked should not be set
        assert not result.get("safety_blocked")
    except Exception as exc:
        # LLM call fails (expected in test env) -- verify it's NOT a shield error
        assert "safety" not in str(exc).lower()


@pytest.mark.asyncio
async def test_output_shield_replaces_unsafe_response(_fresh_graph, monkeypatch):
    """should replace agent response with refusal when output is flagged unsafe."""
    from unittest.mock import AsyncMock

    from langchain_core.messages import AIMessage, HumanMessage

    from src.agents.base import SAFETY_REFUSAL_MESSAGE
    from src.inference.safety import SafetyChecker, SafetyResult

    mock_checker = AsyncMock(spec=SafetyChecker)
    mock_checker.check_input.return_value = SafetyResult(is_safe=True)
    mock_checker.check_output.return_value = SafetyResult(
        is_safe=False, violation_categories=["S6"]
    )
    monkeypatch.setattr("src.agents.base.get_safety_checker", lambda: mock_checker)

    from unittest.mock import MagicMock

    # Mock the classify and agent LLM calls so the graph reaches output_shield.
    # Use MagicMock (not AsyncMock) as the base so sync methods like bind_tools
    # return regular mocks. Only ainvoke needs to be async.
    mock_classifier = MagicMock()
    mock_classifier.ainvoke = AsyncMock(return_value=AIMessage(content="COMPLEX"))

    mock_agent_response = AIMessage(content="Here is some unsafe advice")
    mock_agent_response.tool_calls = []

    mock_agent_llm = MagicMock()
    mock_agent_llm.ainvoke = AsyncMock(return_value=mock_agent_response)
    mock_agent_llm.bind_tools.return_value = mock_agent_llm

    mock_llms = {"fast_small": mock_classifier, "capable_large": mock_agent_llm}
    monkeypatch.setattr(
        "src.agents.public_assistant.get_model_tiers", lambda: ["fast_small", "capable_large"]
    )
    monkeypatch.setattr(
        "src.agents.public_assistant.get_model_config",
        lambda tier: {"model_name": "test", "endpoint": "http://test", "api_key": "key"},
    )

    from src.agents.base import build_routed_graph
    from src.agents.tools import affordability_calc, product_info

    tools = [product_info, affordability_calc]
    tool_descriptions = "\n".join(f"- {t.name}: {t.description}" for t in tools)
    graph = build_routed_graph(
        system_prompt="test",
        tools=tools,
        llms=mock_llms,
        tool_descriptions=tool_descriptions,
    )

    result = await graph.ainvoke({"messages": [HumanMessage(content="give me bad advice")]})

    assert result["messages"][-1].content == SAFETY_REFUSAL_MESSAGE
    mock_checker.check_input.assert_awaited_once()
    mock_checker.check_output.assert_awaited_once()


# -- LLM-based model routing --


def test_classify_prompt_includes_tool_descriptions():
    """The classifier prompt template should have a placeholder for tool descriptions."""
    from src.agents.base import CLASSIFY_PROMPT_TEMPLATE

    assert "{tool_descriptions}" in CLASSIFY_PROMPT_TEMPLATE
    assert "SIMPLE" in CLASSIFY_PROMPT_TEMPLATE
    assert "COMPLEX" in CLASSIFY_PROMPT_TEMPLATE


def test_rule_based_fallback_still_works():
    """Rule-based router remains available as fallback for classifier failures."""
    from src.inference.router import classify_query

    assert classify_query("what is your rate?") == "fast_small"
    assert classify_query("I earn $95k and want to buy a $400k home with 10% down") == (
        "capable_large"
    )
