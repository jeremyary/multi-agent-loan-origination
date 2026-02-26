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


# -- Response parsing (the real logic) --


def test_parse_safe_verdict():
    """should return is_safe=True when Llama Guard says 'safe'."""
    result = SafetyChecker._parse_response("safe")
    assert result.is_safe is True
    assert result.violation_categories == []


def test_parse_unsafe_verdict_with_categories():
    """should return is_safe=False with parsed categories from second line."""
    result = SafetyChecker._parse_response("unsafe\nS1,S3")
    assert result.is_safe is False
    assert result.violation_categories == ["S1", "S3"]


def test_parse_empty_response_treated_as_safe():
    """should treat empty/malformed response as safe (fail-open at parse level)."""
    result = SafetyChecker._parse_response("")
    assert result.is_safe is True


# -- Fail-open behavior (critical design decision) --


@pytest.mark.asyncio
async def test_input_check_fails_open_on_llm_error():
    """should return is_safe=True when the safety model is unreachable."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = ConnectionError("model unreachable")

    checker = SafetyChecker(model="test", endpoint="http://test", api_key="key")
    checker._llm = mock_llm

    result = await checker.check_input("anything")
    assert result.is_safe is True


@pytest.mark.asyncio
async def test_output_check_fails_open_on_llm_error():
    """should return is_safe=True when output check errors."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = RuntimeError("timeout")

    checker = SafetyChecker(model="test", endpoint="http://test", api_key="key")
    checker._llm = mock_llm

    result = await checker.check_output("q", "a")
    assert result.is_safe is True


# -- Prompt formatting (verify correct template is used) --


@pytest.mark.asyncio
async def test_check_input_sends_user_message_in_prompt():
    """should include the user message in the Llama Guard prompt."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AsyncMock(content="safe")

    checker = SafetyChecker(model="test", endpoint="http://test", api_key="key")
    checker._llm = mock_llm

    await checker.check_input("What mortgage rates do you offer?")

    prompt_sent = mock_llm.ainvoke.call_args[0][0]
    assert "What mortgage rates do you offer?" in prompt_sent
    assert "User" in prompt_sent


@pytest.mark.asyncio
async def test_check_input_excludes_privacy_and_advice_categories():
    """Input checks should not flag S6 (Specialized Advice) or S7 (Privacy).

    Users voluntarily provide PII during mortgage intake, and asking for
    mortgage advice is the application's purpose.
    """
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AsyncMock(content="safe")

    checker = SafetyChecker(model="test", endpoint="http://test", api_key="key")
    checker._llm = mock_llm

    await checker.check_input("My SSN is 078-05-1120 and income is $8500/month")

    prompt_sent = mock_llm.ainvoke.call_args[0][0]
    assert "S7: Privacy" not in prompt_sent
    assert "S6: Specialized Advice" not in prompt_sent
    # Other categories should still be present
    assert "S1: Violent Crimes" in prompt_sent


@pytest.mark.asyncio
async def test_check_output_excludes_privacy_and_advice_categories():
    """Output checks should also exclude S6 and S7 for mortgage intake.

    The agent must ask for PII (S7) and provide mortgage guidance (S6) as
    part of its core function.  Data-scope filtering prevents cross-user
    PII leaks at the DB layer; disclaimers are handled in the system prompt.
    """
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AsyncMock(content="safe")

    checker = SafetyChecker(model="test", endpoint="http://test", api_key="key")
    checker._llm = mock_llm

    await checker.check_output("what rates?", "We offer 30-year fixed at 6.5%.")

    prompt_sent = mock_llm.ainvoke.call_args[0][0]
    assert "S7: Privacy" not in prompt_sent
    assert "S6: Specialized Advice" not in prompt_sent
    # Other categories should still be present
    assert "S1: Violent Crimes" in prompt_sent


@pytest.mark.asyncio
async def test_check_output_sends_both_messages_in_prompt():
    """should include both user and assistant messages in the output check prompt."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AsyncMock(content="safe")

    checker = SafetyChecker(model="test", endpoint="http://test", api_key="key")
    checker._llm = mock_llm

    await checker.check_output("what rates?", "We offer 30-year fixed at 6.5%.")

    prompt_sent = mock_llm.ainvoke.call_args[0][0]
    assert "what rates?" in prompt_sent
    assert "We offer 30-year fixed at 6.5%." in prompt_sent
    assert "Agent" in prompt_sent


# -- Factory (config-driven activation) --


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
