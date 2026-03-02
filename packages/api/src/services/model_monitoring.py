# This project was developed with assistance from AI tools.
"""Model monitoring aggregation service (F39).

Pure functions that take LangFuse observation lists and produce Pydantic schemas.
The ``get_model_monitoring_summary`` function orchestrates fetch + aggregate.
"""

import logging
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from ..schemas.model_monitoring import (
    ErrorMetrics,
    ErrorTrendPoint,
    ErrorTypeCount,
    LatencyMetrics,
    LatencyTrendPoint,
    ModelLatencyBreakdown,
    ModelMonitoringSummary,
    ModelRoutingEntry,
    ModelTokenBreakdown,
    RoutingDistribution,
    TokenTrendPoint,
    TokenUsage,
)
from .langfuse_client import fetch_observations

logger = logging.getLogger(__name__)


def _extract_latency_ms(obs: dict[str, Any]) -> float | None:
    """Extract latency in ms from an observation dict.

    LangFuse stores latency as endTime - startTime. Both are ISO timestamps.
    """
    start = obs.get("startTime")
    end = obs.get("endTime")
    if not start or not end:
        return None
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        return (end_dt - start_dt).total_seconds() * 1000
    except (ValueError, TypeError):
        return None


def _extract_tokens(obs: dict[str, Any]) -> tuple[int, int]:
    """Extract (input_tokens, output_tokens) from an observation.

    LangFuse stores usage in the ``usage`` dict with ``input``, ``output``,
    ``inputCost``, ``outputCost`` keys. Some older observations use
    ``promptTokens`` / ``completionTokens``.
    """
    usage = obs.get("usage") or {}
    input_tokens = usage.get("input") or usage.get("promptTokens") or 0
    output_tokens = usage.get("output") or usage.get("completionTokens") or 0
    return int(input_tokens), int(output_tokens)


def _parse_timestamp(ts_str: str | None) -> datetime | None:
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return None


def _bucket_hour(dt: datetime) -> datetime:
    """Truncate a datetime to the hour."""
    return dt.replace(minute=0, second=0, microsecond=0)


def _percentile(values: list[float], p: float) -> float:
    """Compute a percentile from a sorted list of values."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (p / 100)
    f = int(k)
    c = f + 1
    if c >= len(sorted_vals):
        return round(sorted_vals[f], 2)
    d = k - f
    return round(sorted_vals[f] + d * (sorted_vals[c] - sorted_vals[f]), 2)


# ---------------------------------------------------------------------------
# Pure aggregation functions
# ---------------------------------------------------------------------------


def compute_latency_metrics(observations: list[dict[str, Any]]) -> LatencyMetrics:
    """Compute latency percentiles from observations."""
    latencies: list[float] = []
    by_model: dict[str, list[float]] = defaultdict(list)
    by_hour: dict[datetime, list[float]] = defaultdict(list)

    for obs in observations:
        lat = _extract_latency_ms(obs)
        if lat is None or lat < 0:
            continue
        latencies.append(lat)
        model = obs.get("model") or "unknown"
        by_model[model].append(lat)
        ts = _parse_timestamp(obs.get("startTime"))
        if ts:
            by_hour[_bucket_hour(ts)].append(lat)

    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)
    p99 = _percentile(latencies, 99)

    trend = [
        LatencyTrendPoint(
            timestamp=hour,
            p50_ms=_percentile(lats, 50),
            p95_ms=_percentile(lats, 95),
            p99_ms=_percentile(lats, 99),
        )
        for hour, lats in sorted(by_hour.items())
    ]

    model_breakdown = [
        ModelLatencyBreakdown(
            model=model,
            p50_ms=_percentile(lats, 50),
            p95_ms=_percentile(lats, 95),
            p99_ms=_percentile(lats, 99),
            call_count=len(lats),
        )
        for model, lats in sorted(by_model.items())
    ]

    return LatencyMetrics(
        p50_ms=p50,
        p95_ms=p95,
        p99_ms=p99,
        trend=trend,
        by_model=model_breakdown,
    )


def compute_token_usage(observations: list[dict[str, Any]]) -> TokenUsage:
    """Compute token usage totals from observations."""
    total_input = 0
    total_output = 0
    by_model: dict[str, tuple[int, int, int]] = defaultdict(lambda: (0, 0, 0))
    by_hour: dict[datetime, tuple[int, int]] = defaultdict(lambda: (0, 0))

    for obs in observations:
        inp, out = _extract_tokens(obs)
        total_input += inp
        total_output += out

        model = obs.get("model") or "unknown"
        prev = by_model[model]
        by_model[model] = (prev[0] + inp, prev[1] + out, prev[2] + 1)

        ts = _parse_timestamp(obs.get("startTime"))
        if ts:
            hour = _bucket_hour(ts)
            prev_h = by_hour[hour]
            by_hour[hour] = (prev_h[0] + inp, prev_h[1] + out)

    trend = [
        TokenTrendPoint(
            timestamp=hour,
            input_tokens=tokens[0],
            output_tokens=tokens[1],
            total_tokens=tokens[0] + tokens[1],
        )
        for hour, tokens in sorted(by_hour.items())
    ]

    model_breakdown = [
        ModelTokenBreakdown(
            model=model,
            input_tokens=vals[0],
            output_tokens=vals[1],
            total_tokens=vals[0] + vals[1],
            call_count=vals[2],
        )
        for model, vals in sorted(by_model.items())
    ]

    return TokenUsage(
        input_tokens=total_input,
        output_tokens=total_output,
        total_tokens=total_input + total_output,
        trend=trend,
        by_model=model_breakdown,
    )


def compute_error_metrics(observations: list[dict[str, Any]]) -> ErrorMetrics:
    """Compute error rate and top error types from observations."""
    total = len(observations)
    error_types: Counter[str] = Counter()
    by_hour_total: Counter[datetime] = Counter()
    by_hour_errors: Counter[datetime] = Counter()

    for obs in observations:
        ts = _parse_timestamp(obs.get("startTime"))
        hour = _bucket_hour(ts) if ts else None
        if hour:
            by_hour_total[hour] += 1

        level = obs.get("level") or ""
        status_code = obs.get("statusMessage") or ""
        is_error = level == "ERROR" or "error" in str(status_code).lower()

        if is_error:
            error_types[status_code or "Unknown error"] += 1
            if hour:
                by_hour_errors[hour] += 1

    error_count = sum(error_types.values())
    error_rate = round((error_count / total * 100) if total > 0 else 0.0, 2)

    top_errors = [
        ErrorTypeCount(error_type=err, count=cnt) for err, cnt in error_types.most_common(10)
    ]

    trend = [
        ErrorTrendPoint(
            timestamp=hour,
            total_calls=by_hour_total[hour],
            error_count=by_hour_errors.get(hour, 0),
            error_rate=round(
                (by_hour_errors.get(hour, 0) / by_hour_total[hour] * 100)
                if by_hour_total[hour] > 0
                else 0.0,
                2,
            ),
        )
        for hour in sorted(by_hour_total)
    ]

    return ErrorMetrics(
        total_calls=total,
        error_count=error_count,
        error_rate=error_rate,
        top_errors=top_errors,
        trend=trend,
    )


def compute_routing_distribution(
    observations: list[dict[str, Any]],
) -> RoutingDistribution:
    """Compute model routing distribution from observations."""
    model_counts: Counter[str] = Counter()
    for obs in observations:
        model = obs.get("model") or "unknown"
        model_counts[model] += 1

    total = sum(model_counts.values())
    models = [
        ModelRoutingEntry(
            model=model,
            call_count=count,
            percentage=round((count / total * 100) if total > 0 else 0.0, 1),
        )
        for model, count in model_counts.most_common()
    ]

    return RoutingDistribution(models=models, total_calls=total)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def get_model_monitoring_summary(
    hours: int = 24,
    model: str | None = None,
) -> ModelMonitoringSummary:
    """Fetch observations from LangFuse and compute all monitoring metrics.

    Args:
        hours: Time range in hours (1-2160).
        model: Optional model name filter.

    Returns:
        Full monitoring summary. When LangFuse is not configured,
        ``langfuse_available`` is False and all metric fields are None.
    """
    now = datetime.now(UTC)
    start_time = now - timedelta(hours=hours)

    try:
        observations = await fetch_observations(start_time, now, model=model)
    except httpx.HTTPStatusError as exc:
        logger.warning("LangFuse API error: %s", exc)
        raise
    except httpx.RequestError as exc:
        logger.warning("LangFuse connection error: %s", exc)
        raise

    if observations is None:
        return ModelMonitoringSummary(
            langfuse_available=False,
            time_range_hours=hours,
            computed_at=now,
        )

    return ModelMonitoringSummary(
        langfuse_available=True,
        latency=compute_latency_metrics(observations),
        token_usage=compute_token_usage(observations),
        errors=compute_error_metrics(observations),
        routing=compute_routing_distribution(observations),
        time_range_hours=hours,
        computed_at=now,
    )
