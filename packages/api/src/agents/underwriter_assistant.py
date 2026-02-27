# This project was developed with assistance from AI tools.
"""Underwriter assistant -- LangGraph agent for authenticated underwriters.

Tools: uw_queue_view, uw_application_detail, uw_risk_assessment,
uw_preliminary_recommendation, compliance_check, product_info,
affordability_calc, kb_search.
"""

from typing import Any

from .base import build_agent_graph
from .compliance_check_tool import compliance_check
from .compliance_tools import kb_search
from .tools import affordability_calc, product_info
from .underwriter_tools import (
    uw_application_detail,
    uw_preliminary_recommendation,
    uw_queue_view,
    uw_risk_assessment,
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
            uw_risk_assessment,
            uw_preliminary_recommendation,
            compliance_check,
            kb_search,
        ],
        checkpointer=checkpointer,
    )
