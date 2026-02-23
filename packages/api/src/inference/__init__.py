# This project was developed with assistance from AI tools.
"""Inference module -- LLM client, model routing, and config loading."""

from .client import get_completion, get_streaming_completion
from .config import get_model_config, get_routing_config
from .router import classify_query

__all__ = [
    "classify_query",
    "get_completion",
    "get_model_config",
    "get_routing_config",
    "get_streaming_completion",
]
