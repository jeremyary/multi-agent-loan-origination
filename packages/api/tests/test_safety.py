# This project was developed with assistance from AI tools.
"""Tests for safety shields (Llama Guard integration)."""

from unittest.mock import AsyncMock

import pytest

from src.core.config import settings
from src.inference.safety import SafetyChecker, get_safety_checker


@pytest.fixture(autouse=True)
def _disable_auth(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_DISABLED", True)


@pytest.fixture(autouse=True)
def _clear_checker_cache():
    """Reset the module-level checker cache between tests."""
    import src.inference.safety as safety_mod

    safety_mod._checker_instance = None
    yield
    safety_mod._checker_instance = None


# -- SafetyResult parsing --


def test_parse_response_safe():
    """should return is_safe=True when Llama Guard says 'safe'."""
    result = SafetyChecker._parse_response("safe")
    assert result.is_safe is True
    assert result.violation_categories == []


def test_parse_response_unsafe_with_categories():
    """should return is_safe=False with categories when Llama Guard says 'unsafe'."""
    result = SafetyChecker._parse_response("unsafe\nS1,S3")
    assert result.is_safe is False
    assert result.violation_categories == ["S1", "S3"]


def test_parse_response_empty():
    """should treat empty response as safe."""
    result = SafetyChecker._parse_response("")
    assert result.is_safe is True


# -- SafetyChecker.check_input --


@pytest.mark.asyncio
async def test_safety_checker_returns_safe_for_normal_input():
    """should return is_safe=True when Llama Guard classifies input as safe."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AsyncMock(content="safe")

    checker = SafetyChecker(model="test", endpoint="http://test", api_key="key")
    checker._llm = mock_llm

    result = await checker.check_input("What mortgage rates do you offer?")
    assert result.is_safe is True
    assert result.violation_categories == []


@pytest.mark.asyncio
async def test_safety_checker_returns_unsafe_for_harmful_input():
    """should return is_safe=False with categories when input is flagged."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AsyncMock(content="unsafe\nS1")

    checker = SafetyChecker(model="test", endpoint="http://test", api_key="key")
    checker._llm = mock_llm

    result = await checker.check_input("harmful content")
    assert result.is_safe is False
    assert "S1" in result.violation_categories


@pytest.mark.asyncio
async def test_safety_checker_fails_open_on_error():
    """should return is_safe=True when the safety model is unreachable (fail-open)."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = ConnectionError("model unreachable")

    checker = SafetyChecker(model="test", endpoint="http://test", api_key="key")
    checker._llm = mock_llm

    result = await checker.check_input("anything")
    assert result.is_safe is True


# -- SafetyChecker.check_output --


@pytest.mark.asyncio
async def test_safety_checker_output_safe():
    """should return is_safe=True for safe agent output."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AsyncMock(content="safe")

    checker = SafetyChecker(model="test", endpoint="http://test", api_key="key")
    checker._llm = mock_llm

    result = await checker.check_output("what rates?", "We offer 30-year fixed at 6.5%.")
    assert result.is_safe is True


@pytest.mark.asyncio
async def test_safety_checker_output_unsafe():
    """should return is_safe=False when agent output is flagged."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AsyncMock(content="unsafe\nS6")

    checker = SafetyChecker(model="test", endpoint="http://test", api_key="key")
    checker._llm = mock_llm

    result = await checker.check_output("question", "harmful response")
    assert result.is_safe is False
    assert "S6" in result.violation_categories


@pytest.mark.asyncio
async def test_safety_checker_output_fails_open():
    """should return is_safe=True when output check errors (fail-open)."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = RuntimeError("timeout")

    checker = SafetyChecker(model="test", endpoint="http://test", api_key="key")
    checker._llm = mock_llm

    result = await checker.check_output("q", "a")
    assert result.is_safe is True


# -- get_safety_checker factory --


def test_get_safety_checker_returns_none_when_not_configured(monkeypatch):
    """should return None when SAFETY_MODEL is not set."""
    monkeypatch.setattr(settings, "SAFETY_MODEL", None)
    assert get_safety_checker() is None


def test_get_safety_checker_returns_instance_when_configured(monkeypatch):
    """should return a SafetyChecker instance when SAFETY_MODEL is set."""
    monkeypatch.setattr(settings, "SAFETY_MODEL", "meta-llama/Llama-Guard-3-8B")
    monkeypatch.setattr(settings, "SAFETY_ENDPOINT", None)
    monkeypatch.setattr(settings, "SAFETY_API_KEY", None)

    checker = get_safety_checker()
    assert isinstance(checker, SafetyChecker)


def test_get_safety_checker_caches_instance(monkeypatch):
    """should return the same instance on subsequent calls."""
    monkeypatch.setattr(settings, "SAFETY_MODEL", "meta-llama/Llama-Guard-3-8B")
    monkeypatch.setattr(settings, "SAFETY_ENDPOINT", None)
    monkeypatch.setattr(settings, "SAFETY_API_KEY", None)

    first = get_safety_checker()
    second = get_safety_checker()
    assert first is second
