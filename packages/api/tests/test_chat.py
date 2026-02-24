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
