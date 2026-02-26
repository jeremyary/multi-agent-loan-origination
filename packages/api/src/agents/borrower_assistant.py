# This project was developed with assistance from AI tools.
"""Borrower assistant -- LangGraph agent for authenticated borrowers.

Tools: product_info, affordability_calc, start_application,
document_completeness, application_status, regulatory_deadlines,
acknowledge_disclosure, disclosure_status, rate_lock_status,
list_conditions, respond_to_condition_tool, check_condition_satisfaction.
"""

import logging
from typing import Any

from langchain_openai import ChatOpenAI

from ..inference.config import get_model_config, get_model_tiers
from .base import build_routed_graph
from .borrower_tools import (
    acknowledge_disclosure,
    application_status,
    check_condition_satisfaction,
    disclosure_status,
    document_completeness,
    list_conditions,
    rate_lock_status,
    regulatory_deadlines,
    respond_to_condition_tool,
    start_application,
)
from .tools import affordability_calc, product_info

logger = logging.getLogger(__name__)


def build_graph(config: dict[str, Any], checkpointer=None):
    """Build a routed LangGraph graph for the borrower assistant."""
    system_prompt = config.get("system_prompt", "You are a helpful mortgage assistant.")
    tools = [
        product_info,
        affordability_calc,
        start_application,
        document_completeness,
        application_status,
        regulatory_deadlines,
        acknowledge_disclosure,
        disclosure_status,
        rate_lock_status,
        list_conditions,
        respond_to_condition_tool,
        check_condition_satisfaction,
    ]

    tool_descriptions = "\n".join(f"- {t.name}: {t.description}" for t in tools)

    # Extract tool -> allowed_roles mapping from YAML config
    tool_allowed_roles: dict[str, list[str]] = {}
    for tool_cfg in config.get("tools", []):
        name = tool_cfg.get("name")
        allowed = tool_cfg.get("allowed_roles")
        if name and allowed:
            tool_allowed_roles[name] = allowed

    llms: dict[str, ChatOpenAI] = {}
    for tier in get_model_tiers():
        model_cfg = get_model_config(tier)
        llms[tier] = ChatOpenAI(
            model=model_cfg["model_name"],
            base_url=model_cfg["endpoint"],
            api_key=model_cfg.get("api_key", "not-needed"),
        )

    return build_routed_graph(
        system_prompt=system_prompt,
        tools=tools,
        llms=llms,
        tool_descriptions=tool_descriptions,
        tool_allowed_roles=tool_allowed_roles,
        checkpointer=checkpointer,
    )
