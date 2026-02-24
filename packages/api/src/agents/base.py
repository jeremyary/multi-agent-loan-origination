# This project was developed with assistance from AI tools.
"""Custom LangGraph graph with LLM-based per-query model routing.

Graph structure:
    classify (fast LLM) -> agent (routed LLM + tools) <-> tools

The classify node sends the user's message to the fast model with a
prompt listing available tools.  The model replies SIMPLE or COMPLEX,
which selects the tier for the agent node.  All nodes appear in a single
LangFuse trace so the routing decision is visible alongside the response.

If the classifier LLM call fails, routing falls back to the rule-based
classifier in inference.router.
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)

CLASSIFY_PROMPT_TEMPLATE = """\
You are a query router. Decide whether the user's message needs \
tools or complex reasoning.

Available tools:
{tool_descriptions}

Reply with exactly one word: SIMPLE or COMPLEX

SIMPLE: greetings, chitchat, general knowledge questions answerable without tools
COMPLEX: needs data lookup, calculations, comparisons, or multi-step reasoning"""


class AgentState(MessagesState):
    """Graph state extended with a model_tier field set by the classifier."""

    model_tier: str


def build_routed_graph(
    *,
    system_prompt: str,
    tools: list,
    llms: dict[str, ChatOpenAI],
    tool_descriptions: str,
) -> Any:
    """Build a compiled LangGraph graph with LLM-based model routing.

    Args:
        system_prompt: The agent's system prompt (injected per LLM call).
        tools: LangChain tools available to the agent.
        llms: Mapping of tier name to ChatOpenAI instance.
        tool_descriptions: Human-readable tool descriptions for the classifier prompt.

    Returns:
        A compiled StateGraph with classify -> agent <-> tools structure.
    """
    classifier_llm = llms["fast_small"]
    classify_system = CLASSIFY_PROMPT_TEMPLATE.format(tool_descriptions=tool_descriptions)

    async def classify(state: AgentState) -> dict:
        """LLM-based intent classifier -- picks the model tier."""
        last_msg = state["messages"][-1]
        try:
            response = await classifier_llm.ainvoke(
                [
                    SystemMessage(content=classify_system),
                    HumanMessage(content=last_msg.content),
                ]
            )
            text = response.content.upper()
            tier = "fast_small" if "SIMPLE" in text else "capable_large"
        except Exception:
            logger.warning("Classifier LLM failed, falling back to rule-based routing")
            from ..inference.router import classify_query

            tier = classify_query(last_msg.content)

        logger.info("Routed to '%s' for: %s", tier, last_msg.content[:80])
        return {"model_tier": tier}

    async def agent(state: AgentState) -> dict:
        """Call the routed LLM with tools bound."""
        tier = state.get("model_tier", "capable_large")
        llm = llms.get(tier, llms["capable_large"]).bind_tools(tools)
        messages = [SystemMessage(content=system_prompt), *state["messages"]]
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        """Route to tools node if the LLM made tool calls, else end."""
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    tool_node = ToolNode(tools)

    graph = StateGraph(AgentState)
    graph.add_node("classify", classify)
    graph.add_node("agent", agent)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()
