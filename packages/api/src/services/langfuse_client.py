# This project was developed with assistance from AI tools.
"""LangFuse API client for fetching observation data.

Purpose-built client with a single method to fetch LLM generation observations.
Uses Basic auth (public_key:secret_key) per the LangFuse public API spec.
Includes a 60-second in-memory TTL cache to avoid repeated API calls on
dashboard refreshes.
"""

import logging
import time
from base64 import b64encode
from datetime import UTC, datetime
from typing import Any

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)

# In-memory TTL cache: (cache_key -> (timestamp, data))
_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_CACHE_TTL_SECONDS = 60


def _is_configured() -> bool:
    """Check whether LangFuse API keys and host are configured."""
    return bool(
        settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY and settings.LANGFUSE_HOST
    )


def _auth_header() -> str:
    """Build Basic auth header value from LangFuse keys."""
    creds = f"{settings.LANGFUSE_PUBLIC_KEY}:{settings.LANGFUSE_SECRET_KEY}"
    encoded = b64encode(creds.encode()).decode()
    return f"Basic {encoded}"


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


async def fetch_observations(
    start_time: datetime,
    end_time: datetime,
    model: str | None = None,
) -> list[dict[str, Any]] | None:
    """Fetch LLM generation observations from LangFuse API.

    Args:
        start_time: Start of the time range (UTC).
        end_time: End of the time range (UTC).
        model: Optional model name filter.

    Returns:
        List of observation dicts, or None if LangFuse is not configured.

    Raises:
        httpx.HTTPStatusError: If LangFuse returns a non-2xx response.
    """
    if not _is_configured():
        return None

    key = _cache_key(start_time, end_time, model)
    cached = _get_cached(key)
    if cached is not None:
        return cached

    params: dict[str, Any] = {
        "type": "GENERATION",
        "fromStartTime": start_time.astimezone(UTC).isoformat(),
        "toStartTime": end_time.astimezone(UTC).isoformat(),
    }
    if model:
        params["model"] = model

    base_url = settings.LANGFUSE_HOST.rstrip("/")
    url = f"{base_url}/api/public/observations"

    all_observations: list[dict[str, Any]] = []
    page = 1

    async with httpx.AsyncClient(timeout=15.0) as client:
        while True:
            params["page"] = page
            response = await client.get(
                url,
                params=params,
                headers={"Authorization": _auth_header()},
            )
            response.raise_for_status()
            body = response.json()
            data = body.get("data", [])
            all_observations.extend(data)

            meta = body.get("meta", {})
            total_pages = meta.get("totalPages", 1)
            if page >= total_pages:
                break
            page += 1

    _set_cached(key, all_observations)
    return all_observations


def clear_cache() -> None:
    """Clear the observation cache (for testing)."""
    _cache.clear()
