# This project was developed with assistance from AI tools.
"""Tests for MLFlow client for fetching trace data."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.core.config import settings
from src.services.mlflow_client import (
    _is_configured,
    _trace_to_observation,
    clear_cache,
    fetch_traces,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear cache before each test."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture(autouse=True)
def _disable_auth(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_DISABLED", True)


def test_is_configured_returns_false_when_no_uri(monkeypatch):
    """should return False when MLFLOW_TRACKING_URI is not set."""
    monkeypatch.setattr(settings, "MLFLOW_TRACKING_URI", None)
    assert _is_configured() is False


def test_is_configured_returns_true_when_uri_set(monkeypatch):
    """should return True when MLFLOW_TRACKING_URI is set."""
    monkeypatch.setattr(settings, "MLFLOW_TRACKING_URI", "http://localhost:5000")
    assert _is_configured() is True


@pytest.mark.asyncio
async def test_fetch_traces_returns_none_when_unconfigured(monkeypatch):
    """should return None when MLFlow is not configured."""
    monkeypatch.setattr(settings, "MLFLOW_TRACKING_URI", None)

    now = datetime.now(UTC)
    start = now - timedelta(hours=1)

    result = await fetch_traces(start, now)
    assert result is None


@pytest.mark.asyncio
@patch("mlflow.MlflowClient")
async def test_fetch_traces_searches_and_converts(mock_client_cls, monkeypatch):
    """should search traces and convert to observation format."""
    monkeypatch.setattr(settings, "MLFLOW_TRACKING_URI", "http://localhost:5000")

    # Create mock trace
    mock_trace = MagicMock()
    mock_trace.info.timestamp_ms = 1700000000000
    mock_trace.info.execution_time_ms = 150
    mock_trace.info.status.status_code = "OK"

    mock_span = MagicMock()
    mock_span.attributes = {
        "llm.token_count.prompt": 100,
        "llm.token_count.completion": 50,
        "llm.model": "gpt-4",
    }
    mock_trace.data.spans = [mock_span]

    mock_client = MagicMock()
    mock_client.search_traces.return_value = [mock_trace]
    mock_client_cls.return_value = mock_client

    now = datetime.now(UTC)
    start = now - timedelta(hours=1)

    result = await fetch_traces(start, now)

    assert result is not None
    assert len(result) == 1
    assert result[0]["model"] == "gpt-4"
    assert result[0]["usage"]["input"] == 100
    assert result[0]["usage"]["output"] == 50


@pytest.mark.asyncio
@patch("mlflow.MlflowClient")
async def test_fetch_traces_applies_model_filter(mock_client_cls, monkeypatch):
    """should filter traces by model name."""
    monkeypatch.setattr(settings, "MLFLOW_TRACKING_URI", "http://localhost:5000")

    # Create two mock traces with different models
    mock_trace1 = MagicMock()
    mock_trace1.info.timestamp_ms = 1700000000000
    mock_trace1.info.execution_time_ms = 100
    mock_trace1.info.status.status_code = "OK"
    mock_span1 = MagicMock()
    mock_span1.attributes = {"llm.model": "gpt-4"}
    mock_trace1.data.spans = [mock_span1]

    mock_trace2 = MagicMock()
    mock_trace2.info.timestamp_ms = 1700000001000
    mock_trace2.info.execution_time_ms = 80
    mock_trace2.info.status.status_code = "OK"
    mock_span2 = MagicMock()
    mock_span2.attributes = {"llm.model": "gpt-3.5-turbo"}
    mock_trace2.data.spans = [mock_span2]

    mock_client = MagicMock()
    mock_client.search_traces.return_value = [mock_trace1, mock_trace2]
    mock_client_cls.return_value = mock_client

    now = datetime.now(UTC)
    start = now - timedelta(hours=1)

    result = await fetch_traces(start, now, model="gpt-4")

    assert result is not None
    assert len(result) == 1
    assert result[0]["model"] == "gpt-4"


@pytest.mark.asyncio
@patch("mlflow.MlflowClient")
async def test_fetch_traces_uses_cache(mock_client_cls, monkeypatch):
    """should return cached data on second call."""
    monkeypatch.setattr(settings, "MLFLOW_TRACKING_URI", "http://localhost:5000")

    mock_trace = MagicMock()
    mock_trace.info.timestamp_ms = 1700000000000
    mock_trace.info.execution_time_ms = 100
    mock_trace.info.status.status_code = "OK"
    mock_trace.data.spans = []

    mock_client = MagicMock()
    mock_client.search_traces.return_value = [mock_trace]
    mock_client_cls.return_value = mock_client

    now = datetime.now(UTC)
    start = now - timedelta(hours=1)

    # First call
    await fetch_traces(start, now)
    # Second call should use cache
    await fetch_traces(start, now)

    # Should only have been called once due to caching
    assert mock_client.search_traces.call_count == 1


@pytest.mark.asyncio
@patch("mlflow.MlflowClient")
async def test_fetch_traces_catches_errors(mock_client_cls, monkeypatch):
    """should return None and log warning when API fails."""
    monkeypatch.setattr(settings, "MLFLOW_TRACKING_URI", "http://localhost:5000")

    mock_client = MagicMock()
    mock_client.search_traces.side_effect = RuntimeError("connection failed")
    mock_client_cls.return_value = mock_client

    now = datetime.now(UTC)
    start = now - timedelta(hours=1)

    result = await fetch_traces(start, now)
    assert result is None


def test_trace_to_observation_extracts_fields():
    """should extract all fields from trace correctly."""
    mock_trace = MagicMock()
    mock_trace.info.timestamp_ms = 1700000000000
    mock_trace.info.execution_time_ms = 250
    mock_trace.info.status.status_code = "OK"

    mock_span = MagicMock()
    mock_span.attributes = {
        "llm.token_count.prompt": 200,
        "llm.token_count.completion": 100,
        "llm.model": "llama-3.1-70b",
    }
    mock_trace.data.spans = [mock_span]

    obs = _trace_to_observation(mock_trace)

    assert obs["model"] == "llama-3.1-70b"
    assert obs["usage"]["input"] == 200
    assert obs["usage"]["output"] == 100
    assert obs["level"] == "DEFAULT"
    assert obs["startTime"] is not None
    assert obs["endTime"] is not None


def test_trace_to_observation_handles_error_status():
    """should set level to ERROR when trace has error status."""
    mock_trace = MagicMock()
    mock_trace.info.timestamp_ms = 1700000000000
    mock_trace.info.execution_time_ms = 50
    mock_trace.info.status.status_code = "ERROR"
    mock_trace.data.spans = []

    obs = _trace_to_observation(mock_trace)

    assert obs["level"] == "ERROR"


def test_trace_to_observation_handles_missing_spans():
    """should handle traces with no spans gracefully."""
    mock_trace = MagicMock()
    mock_trace.info.timestamp_ms = 1700000000000
    mock_trace.info.execution_time_ms = 100
    mock_trace.info.status.status_code = "OK"
    mock_trace.data.spans = []

    obs = _trace_to_observation(mock_trace)

    assert obs["model"] is None
    assert obs["usage"]["input"] == 0
    assert obs["usage"]["output"] == 0
