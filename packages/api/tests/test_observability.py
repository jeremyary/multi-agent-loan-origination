# This project was developed with assistance from AI tools.
"""Tests for LangFuse observability integration."""

from unittest.mock import MagicMock, patch

import pytest

from src.core.config import settings
from src.observability import build_langfuse_config, flush_langfuse


@pytest.fixture(autouse=True)
def _disable_auth(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_DISABLED", True)


def test_build_config_returns_empty_when_unconfigured(monkeypatch):
    """should return {} when LangFuse keys are not set."""
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", None)
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", None)

    config = build_langfuse_config(session_id="test-session")
    assert config == {}


def test_build_config_returns_empty_when_partial_config(monkeypatch):
    """should return {} when only public key is set (no secret)."""
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", None)

    config = build_langfuse_config(session_id="test-session")
    assert config == {}


@patch("langfuse.langchain.CallbackHandler")
def test_build_config_returns_callbacks_when_configured(mock_cls, monkeypatch):
    """should return config with callbacks and metadata when both keys are set."""
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", "sk-lf-test")
    monkeypatch.setattr(settings, "LANGFUSE_HOST", "http://localhost:3001")

    mock_handler = MagicMock()
    mock_cls.return_value = mock_handler

    config = build_langfuse_config(session_id="sess-123", user_id="user-1")

    assert config["callbacks"] == [mock_handler]
    assert config["metadata"]["langfuse_session_id"] == "sess-123"
    assert config["metadata"]["langfuse_user_id"] == "user-1"
    mock_cls.assert_called_once()


@patch("langfuse.langchain.CallbackHandler")
def test_build_config_omits_optional_metadata(mock_cls, monkeypatch):
    """should not include user_id or tags in metadata when not provided."""
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", "sk-lf-test")
    mock_cls.return_value = MagicMock()

    config = build_langfuse_config(session_id="sess-456")

    assert "langfuse_user_id" not in config["metadata"]
    assert "langfuse_tags" not in config["metadata"]


@patch("langfuse.langchain.CallbackHandler")
def test_build_config_catches_init_error(mock_cls, monkeypatch):
    """should return {} and log warning if CallbackHandler init fails."""
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", "sk-lf-test")
    mock_cls.side_effect = RuntimeError("connection refused")

    config = build_langfuse_config(session_id="sess-err")
    assert config == {}


def test_flush_noop_when_unconfigured(monkeypatch):
    """should not raise when flushing with no keys configured."""
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", None)
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", None)
    flush_langfuse()


@patch("langfuse.get_client")
def test_flush_calls_client_flush(mock_get_client, monkeypatch):
    """should call get_client().flush() when configured."""
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", "sk-lf-test")
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    flush_langfuse()

    mock_client.flush.assert_called_once()


@patch("langfuse.get_client")
def test_flush_swallows_errors(mock_get_client, monkeypatch):
    """should not raise when flush() throws."""
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", "sk-lf-test")
    mock_get_client.side_effect = RuntimeError("network error")
    flush_langfuse()
