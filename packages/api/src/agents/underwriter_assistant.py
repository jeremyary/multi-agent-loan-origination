# This project was developed with assistance from AI tools.
"""Underwriter assistant -- LangGraph agent for authenticated underwriters.

Tools: uw_queue_view, uw_application_detail, product_info,
affordability_calc, kb_search.
"""

from typing import Any

from .base import build_agent_graph
from .compliance_tools import kb_search
from .tools import affordability_calc, product_info
from .underwriter_tools import (
    uw_application_detail,
    uw_queue_view,
)


def build_graph(config: dict[str, Any], checkpointer=None):
    """Build a routed LangGraph graph for the underwriter assistant."""
    return build_agent_graph(
        config,
        [
            product_info,
            affordability_calc,
            uw_queue_view,
            uw_application_detail,
            kb_search,
        ],
        checkpointer=checkpointer,
    )
