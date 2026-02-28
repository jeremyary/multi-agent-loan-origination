# This project was developed with assistance from AI tools.
"""CEO executive assistant -- LangGraph agent for authenticated CEO users.

Tools: ceo_pipeline_summary, ceo_denial_trends, ceo_lo_performance,
ceo_application_lookup, ceo_audit_trail, ceo_decision_trace,
ceo_audit_search, product_info.
"""

from typing import Any

from .base import build_agent_graph
from .ceo_tools import (
    ceo_application_lookup,
    ceo_audit_search,
    ceo_audit_trail,
    ceo_decision_trace,
    ceo_denial_trends,
    ceo_lo_performance,
    ceo_pipeline_summary,
)
from .tools import product_info


def build_graph(config: dict[str, Any], checkpointer=None):
    """Build a routed LangGraph graph for the CEO assistant."""
    return build_agent_graph(
        config,
        [
            ceo_pipeline_summary,
            ceo_denial_trends,
            ceo_lo_performance,
            ceo_application_lookup,
            ceo_audit_trail,
            ceo_decision_trace,
            ceo_audit_search,
            product_info,
        ],
        checkpointer=checkpointer,
    )
