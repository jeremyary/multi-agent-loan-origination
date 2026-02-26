# This project was developed with assistance from AI tools.
"""Public assistant -- LangGraph agent for unauthenticated prospects.

Tools: product_info, affordability_calc (no customer data access).
"""

from typing import Any

from .base import build_agent_graph
from .tools import affordability_calc, product_info


def build_graph(config: dict[str, Any], checkpointer=None):
    """Build a routed LangGraph graph for the public assistant."""
    return build_agent_graph(
        config,
        [product_info, affordability_calc],
        checkpointer=checkpointer,
    )
