# This project was developed with assistance from AI tools.
"""Public assistant -- LangGraph agent for unauthenticated prospects.

Tools: product_info, affordability_calc (no customer data access).
"""

import logging
from typing import Any

from langchain_openai import ChatOpenAI

from ..inference.config import get_model_config, get_model_tiers
from .base import build_routed_graph
from .tools import affordability_calc, product_info

logger = logging.getLogger(__name__)


def build_graph(config: dict[str, Any]):
    """Build a routed LangGraph graph for the public assistant."""
    system_prompt = config.get("system_prompt", "You are a helpful mortgage assistant.")
    tools = [product_info, affordability_calc]

    tool_descriptions = "\n".join(f"- {t.name}: {t.description}" for t in tools)

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
    )
