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


def classify_query(query: str) -> str:
    """Classify a query and return the model tier name.

    Uses a three-rule cascade:
      1. Complex keywords (tool-requiring terms) -> capable tier
      2. Word count exceeds threshold -> capable tier
      3. Simple pattern match -> fast tier
      4. Default -> capable tier (safe fallback)

    Args:
        query: The user's message text.

    Returns:
        Model tier key (e.g. 'fast_small' or 'capable_large').
    """
    routing = get_routing_config()
    classification = routing.get("classification", {})
    rules = classification.get("rules", {})
    simple_rules = rules.get("simple", {})
    complex_rules = rules.get("complex", {})
    query_lower = query.lower()

    # Rule 1: Complex keywords always route to capable
    complex_keywords = complex_rules.get("keywords", [])
    if any(kw in query_lower for kw in complex_keywords):
        return _complex_tier(routing)

    # Rule 2: Word count exceeds threshold -> capable
    max_words = simple_rules.get("max_query_words", 10)
    if len(query.split()) > max_words:
        return _complex_tier(routing)

    # Rule 3: Simple pattern match -> fast tier
    patterns = simple_rules.get("patterns", [])
    if any(pattern in query_lower for pattern in patterns):
        return "fast_small"

    # Default to complex (safe fallback)
    return _complex_tier(routing)


def _complex_tier(routing: dict) -> str:
    """Return the complex/default tier name."""
    return routing.get("default_tier", "capable_large")
