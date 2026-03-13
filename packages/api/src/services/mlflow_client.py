# This project was developed with assistance from AI tools.
"""MLFlow API client for fetching trace data.

Purpose-built client with a single method to fetch LLM generation traces.
Uses MlflowClient.search_traces() API for querying trace data.
Includes a 60-second in-memory TTL cache to avoid repeated API calls on
dashboard refreshes.
"""

import logging
import time
from datetime import UTC, datetime
from typing import Any

from ..core.config import settings

logger = logging.getLogger(__name__)

# In-memory TTL cache: (cache_key -> (timestamp, data))
_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_CACHE_TTL_SECONDS = 60


def _is_configured() -> bool:
    """Check whether MLFlow tracking URI is configured."""
    return bool(settings.MLFLOW_TRACKING_URI)


def _cache_key(start_time: datetime, end_time: datetime, model: str | None) -> str:
    return f"{start_time.isoformat()}|{end_time.isoformat()}|{model or ''}"


def _get_cached(key: str) -> list[dict[str, Any]] | None:
    """Return cached data if within TTL, else None."""
    if key in _cache:
        ts, data = _cache[key]
        if time.monotonic() - ts < _CACHE_TTL_SECONDS:
            return data
        del _cache[key]
    return None


def _set_cached(key: str, data: list[dict[str, Any]]) -> None:
    """Store data in cache with current timestamp."""
    _cache[key] = (time.monotonic(), data)


def _trace_to_observation(trace: Any) -> dict[str, Any]:
    """Convert an MLFlow trace to LangFuse-compatible observation dict.

    Maps MLFlow trace attributes to the structure expected by model_monitoring.py.
    This allows the downstream aggregation functions to work unchanged.

    Args:
        trace: MLFlow Trace object from search_traces().

    Returns:
        Dict matching LangFuse observation structure for compatibility.
    """
    # Extract timestamps
    start_time = None
    end_time = None
    if hasattr(trace, "info"):
        if hasattr(trace.info, "timestamp_ms") and trace.info.timestamp_ms:
            start_time = datetime.fromtimestamp(trace.info.timestamp_ms / 1000, tz=UTC).isoformat()
        if hasattr(trace.info, "execution_time_ms") and trace.info.execution_time_ms:
            exec_ms = trace.info.execution_time_ms
            if start_time and trace.info.timestamp_ms:
                end_ts = (trace.info.timestamp_ms + exec_ms) / 1000
                end_time = datetime.fromtimestamp(end_ts, tz=UTC).isoformat()

    # Extract token counts and model from span attributes
    input_tokens = 0
    output_tokens = 0
    model_name = None
    level = "DEFAULT"

    # Check trace status
    if hasattr(trace, "info") and hasattr(trace.info, "status"):
        status = trace.info.status
        if hasattr(status, "status_code"):
            if str(status.status_code) == "ERROR":
                level = "ERROR"

    # Iterate through spans to find LLM spans
    if hasattr(trace, "data") and hasattr(trace.data, "spans"):
        for span in trace.data.spans:
            attrs = getattr(span, "attributes", {}) or {}
            # MLFlow LangChain integration uses these attribute keys
            if "llm.token_count.prompt" in attrs:
                input_tokens += int(attrs.get("llm.token_count.prompt", 0))
            if "llm.token_count.completion" in attrs:
                output_tokens += int(attrs.get("llm.token_count.completion", 0))
            if "llm.model" in attrs and not model_name:
                model_name = attrs.get("llm.model")

    return {
        "startTime": start_time,
        "endTime": end_time,
        "model": model_name,
        "level": level,
        "usage": {
            "input": input_tokens,
            "output": output_tokens,
        },
    }


async def fetch_traces(
    start_time: datetime,
    end_time: datetime,
    model: str | None = None,
) -> list[dict[str, Any]] | None:
    """Fetch LLM traces from MLFlow API.

    Args:
        start_time: Start of the time range (UTC).
        end_time: End of the time range (UTC).
        model: Optional model name filter.

    Returns:
        List of observation-compatible dicts, or None if MLFlow is not configured.
    """
    if not _is_configured():
        return None

    key = _cache_key(start_time, end_time, model)
    cached = _get_cached(key)
    if cached is not None:
        return cached

    try:
        from mlflow import MlflowClient

        client = MlflowClient(tracking_uri=settings.MLFLOW_TRACKING_URI)

        # Build filter string for time range
        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)
        filter_string = f"timestamp_ms >= {start_ms} AND timestamp_ms <= {end_ms}"

        # Search traces in the configured experiment
        traces = client.search_traces(
            experiment_ids=[],  # Empty list searches all experiments
            filter_string=filter_string,
            max_results=1000,
        )

        # Convert traces to observation format
        observations = []
        for trace in traces:
            obs = _trace_to_observation(trace)
            # Apply model filter if specified
            if model and obs.get("model") != model:
                continue
            observations.append(obs)

        _set_cached(key, observations)
        return observations

    except Exception:
        logger.warning("Failed to fetch MLFlow traces", exc_info=True)
        return None


def clear_cache() -> None:
    """Clear the trace cache (for testing)."""
    _cache.clear()
