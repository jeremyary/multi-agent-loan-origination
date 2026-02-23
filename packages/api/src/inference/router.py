# This project was developed with assistance from AI tools.
"""Rule-based query classifier for model routing.

Classifies user queries as 'simple' or 'complex' to select the
appropriate model tier.  Both tiers currently point to the same model
for local dev; the routing logic is in place for when two models are
available.

Fallback behaviour (per S-1-F21-02):
  - complex model unavailable -> error
  - simple model unavailable  -> fallback to complex
"""

import logging

from .config import get_routing_config

logger = logging.getLogger(__name__)


def classify_query(query: str, requires_tools: bool = False) -> str:
    """Classify a query and return the model tier name.

    Args:
        query: The user's message text.
        requires_tools: Whether the agent needs tool-calling for this query.

    Returns:
        Model tier key (e.g. 'fast_small' or 'capable_large').
    """
    routing = get_routing_config()
    classification = routing.get("classification", {})
    rules = classification.get("rules", {})
    simple_rules = rules.get("simple", {})

    # If tools are required, always use complex tier
    if requires_tools:
        return _complex_tier(routing)

    # Word count check
    max_words = simple_rules.get("max_query_words", 10)
    if len(query.split()) > max_words:
        return _complex_tier(routing)

    # Pattern matching -- if query contains any simple pattern, route to fast tier
    patterns = simple_rules.get("patterns", [])
    query_lower = query.lower()
    if any(pattern in query_lower for pattern in patterns):
        return "fast_small"

    # Default to complex
    return _complex_tier(routing)


def _complex_tier(routing: dict) -> str:
    """Return the complex/default tier name."""
    return routing.get("default_tier", "capable_large")
