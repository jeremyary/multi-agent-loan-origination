# This project was developed with assistance from AI tools.
"""Public assistant -- LangGraph ReAct agent for unauthenticated prospects.

Tools: product_info, affordability_calc (no customer data access).
"""

import logging
from typing import Any

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from ..inference.config import get_model_config
from .tools import affordability_calc, product_info

logger = logging.getLogger(__name__)


def build_graph(config: dict[str, Any]):
    """Build a compiled LangGraph graph for the public assistant."""
    system_prompt = config.get("system_prompt", "You are a helpful mortgage assistant.")
    tools = [product_info, affordability_calc]

    # Determine which model tier to use (can be overridden per-query later)
    model_cfg = get_model_config("fast_small")
    llm = ChatOpenAI(
        model=model_cfg["model_name"],
        base_url=model_cfg["endpoint"],
        api_key=model_cfg.get("api_key", "not-needed"),
    )

    graph = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )
    return graph
