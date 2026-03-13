# This project was developed with assistance from AI tools.
"""MLFlow observability integration.

Provides automatic tracing for LangGraph/LangChain via MLFlow autolog.
When MLFLOW_TRACKING_URI is set, all LangChain operations are automatically
traced without requiring explicit callbacks.

Design principle (mirrors safety.py): tracing is active when MLFLOW_TRACKING_URI
is set, degrades gracefully (no-op + warning) when not configured, and never
blocks the conversation on a tracing error.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_autolog_enabled = False


def _is_configured() -> bool:
    """Return True when MLFlow tracking URI is set."""
    from .core.config import settings

    return bool(settings.MLFLOW_TRACKING_URI)


def init_mlflow_tracing() -> None:
    """Initialize MLFlow autolog for LangChain/LangGraph tracing.

    Call once at application startup. When MLFLOW_TRACKING_URI is configured,
    this enables automatic tracing of all LangChain operations via autolog.
    """
    global _autolog_enabled

    if not _is_configured():
        return

    try:
        import mlflow
        import mlflow.langchain

        from .core.config import settings

        # MLFlow reads auth settings from OS environment variables directly,
        # so we must set them before calling any mlflow functions.
        if settings.MLFLOW_TRACKING_TOKEN:
            os.environ["MLFLOW_TRACKING_TOKEN"] = settings.MLFLOW_TRACKING_TOKEN
        if settings.MLFLOW_WORKSPACE:
            os.environ["MLFLOW_WORKSPACE"] = settings.MLFLOW_WORKSPACE
        if settings.MLFLOW_TRACKING_INSECURE_TLS:
            os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "true"

        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)
        mlflow.langchain.autolog()
        _autolog_enabled = True
        logger.debug("MLFlow autolog initialized")
    except Exception:
        logger.warning("Failed to initialize MLFlow tracing", exc_info=True)


def set_trace_context(
    *,
    session_id: str,
    user_id: str | None = None,
    tags: list[str] | None = None,
) -> None:
    """Set MLFlow tags for trace correlation.

    Args:
        session_id: Correlates all messages within a WebSocket session.
        user_id: Optional user identifier attached to the trace.
        tags: Optional list of tags for filtering traces.

    Note:
        With autolog, traces are created automatically. This function sets
        tags on the active run for correlation and filtering in the MLFlow UI.
    """
    if not _autolog_enabled:
        return

    try:
        import mlflow

        mlflow.set_tag("session_id", session_id)
        if user_id:
            mlflow.set_tag("user_id", user_id)
        if tags:
            mlflow.set_tag("tags", ",".join(tags))
    except Exception:
        logger.debug("Failed to set MLFlow trace context", exc_info=True)


def log_observability_status() -> None:
    """Log whether MLFlow tracing is active or disabled. Call at startup."""
    from .core.config import settings

    if settings.MLFLOW_TRACKING_URI:
        status = "ACTIVE" if _autolog_enabled else "CONFIGURED (autolog pending)"
        logger.info(
            "MLFlow tracing: %s (uri=%s, experiment=%s)",
            status,
            settings.MLFLOW_TRACKING_URI,
            settings.MLFLOW_EXPERIMENT_NAME,
        )
    else:
        logger.info("MLFlow tracing: DISABLED (MLFLOW_TRACKING_URI not set)")
