# This project was developed with assistance from AI tools.
"""LangFuse observability integration.

Provides helpers for building LangGraph run configs with LangFuse tracing.
The CallbackHandler plugs into ``astream_events()`` via the
``config={"callbacks": [...]}`` parameter.

In LangFuse v3 the SDK is initialised once via environment variables or
``langfuse.get_client()``; session/user IDs are passed as metadata keys
(``langfuse_session_id``, ``langfuse_user_id``) in the run config.

Design principle (mirrors safety.py): tracing is active when LANGFUSE_PUBLIC_KEY
and LANGFUSE_SECRET_KEY are set, degrades gracefully (no-op + warning) when not
configured, and never blocks the conversation on a tracing error.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _is_configured() -> bool:
    """Return True when both LangFuse keys are set."""
    from .core.config import settings

    return bool(settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY)


def build_langfuse_config(
    *,
    session_id: str,
    user_id: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Build a LangGraph run config dict with LangFuse callbacks, or empty dict.

    Args:
        session_id: Correlates all messages within a WebSocket session.
        user_id: Optional user identifier attached to the trace.
        tags: Optional list of tags visible in the LangFuse UI.

    Returns:
        A config dict ready to spread into ``astream_events(config=...)``,
        or ``{}`` when LangFuse is not configured.
    """
    if not _is_configured():
        return {}

    try:
        from langfuse.langchain import CallbackHandler

        handler = CallbackHandler()
        metadata: dict[str, Any] = {"langfuse_session_id": session_id}
        if user_id:
            metadata["langfuse_user_id"] = user_id
        if tags:
            metadata["langfuse_tags"] = tags
        return {"callbacks": [handler], "metadata": metadata}
    except Exception:
        logger.warning("Failed to create LangFuse handler, tracing disabled", exc_info=True)
        return {}


def flush_langfuse() -> None:
    """Flush pending LangFuse events.  No-op if unconfigured."""
    if not _is_configured():
        return
    try:
        from langfuse import get_client

        get_client().flush()
    except Exception:
        logger.debug("LangFuse flush failed", exc_info=True)


def log_observability_status() -> None:
    """Log whether LangFuse tracing is active or disabled. Call at startup."""
    from .core.config import settings

    if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
        logger.warning(
            "LangFuse tracing: ACTIVE (host=%s)",
            settings.LANGFUSE_HOST or "https://cloud.langfuse.com",
        )
    else:
        logger.warning("LangFuse tracing: DISABLED (keys not configured)")
