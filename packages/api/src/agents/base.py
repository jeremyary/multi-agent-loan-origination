# This project was developed with assistance from AI tools.
"""Custom LangGraph graph with safety shields and LLM-based per-query model routing.

Graph structure:
    input_shield -> classify (fast LLM) -> agent (routed LLM + tools) <-> tools
         |                                          |
         +-(blocked)-> END                          +-(done)-> output_shield -> END

The input_shield node calls Llama Guard on the user's message.  If unsafe, it
short-circuits to END with a refusal message.  The output_shield node checks the
agent's completed response and replaces it with a refusal if unsafe.

Shields are active when SAFETY_MODEL is configured; otherwise they are no-ops.
On any safety-model error the check is skipped (fail-open).

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

from ..inference.safety import get_safety_checker

logger = logging.getLogger(__name__)

CLASSIFY_PROMPT_TEMPLATE = """\
You are a query router. Decide whether the user's message needs \
tools or complex reasoning.

Available tools:
{tool_descriptions}

Reply with exactly one word: SIMPLE or COMPLEX

SIMPLE: greetings, chitchat, general knowledge questions answerable without tools
COMPLEX: needs data lookup, calculations, comparisons, or multi-step reasoning"""

SAFETY_REFUSAL_MESSAGE = (
    "I'm not able to help with that request. Can I assist you with something else?"
)


class AgentState(MessagesState):
    """Graph state extended with model routing and safety fields."""

    model_tier: str
    safety_blocked: bool


def build_routed_graph(
    *,
    system_prompt: str,
    tools: list,
    llms: dict[str, ChatOpenAI],
    tool_descriptions: str,
) -> Any:
    """Build a compiled LangGraph graph with safety shields and LLM-based model routing.

    Args:
        system_prompt: The agent's system prompt (injected per LLM call).
        tools: LangChain tools available to the agent.
        llms: Mapping of tier name to ChatOpenAI instance.
        tool_descriptions: Human-readable tool descriptions for the classifier prompt.

    Returns:
        A compiled StateGraph with input_shield -> classify -> agent <-> tools
        -> output_shield structure.
    """
    classifier_llm = llms["fast_small"]
    classify_system = CLASSIFY_PROMPT_TEMPLATE.format(tool_descriptions=tool_descriptions)

    async def input_shield(state: AgentState) -> dict:
        """Check user input against Llama Guard safety categories."""
        checker = get_safety_checker()
        if not checker:
            return {}

        last_msg = state["messages"][-1]
        result = await checker.check_input(last_msg.content)
        if not result.is_safe:
            logger.warning("Input shield BLOCKED: categories=%s", result.violation_categories)
            return {
                "safety_blocked": True,
                "messages": [AIMessage(content=SAFETY_REFUSAL_MESSAGE)],
            }
        logger.debug("Input shield: safe")
        return {}

    def after_input_shield(state: AgentState) -> str:
        """Route to END if input was blocked, otherwise continue to classify."""
        if state.get("safety_blocked"):
            return END
        return "classify"

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
        """Route to tools node if the LLM made tool calls, else to output shield."""
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return "output_shield"

    async def output_shield(state: AgentState) -> dict:
        """Check agent output against Llama Guard safety categories."""
        checker = get_safety_checker()
        if not checker:
            return {}

        last_msg = state["messages"][-1]
        if not isinstance(last_msg, AIMessage) or not last_msg.content:
            return {}

        user_msg = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                user_msg = msg.content
                break

        result = await checker.check_output(user_msg, last_msg.content)
        if not result.is_safe:
            logger.warning("Output shield BLOCKED: categories=%s", result.violation_categories)
            return {"messages": [AIMessage(content=SAFETY_REFUSAL_MESSAGE)]}
        logger.debug("Output shield: safe")
        return {}

    tool_node = ToolNode(tools)

    graph = StateGraph(AgentState)
    graph.add_node("input_shield", input_shield)
    graph.add_node("classify", classify)
    graph.add_node("agent", agent)
    graph.add_node("tools", tool_node)
    graph.add_node("output_shield", output_shield)

    graph.set_entry_point("input_shield")
    graph.add_conditional_edges(
        "input_shield", after_input_shield, {END: END, "classify": "classify"}
    )
    graph.add_edge("classify", "agent")
    graph.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", "output_shield": "output_shield"}
    )
    graph.add_edge("tools", "agent")
    graph.add_edge("output_shield", END)

    return graph.compile()
