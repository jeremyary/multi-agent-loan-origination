# This project was developed with assistance from AI tools.
"""Custom LangGraph graph with safety shields and two-pass model routing.

Graph structure:
    input_shield -> classify (fast LLM) -> agent_fast / agent_capable
         |                                          |
         +-(blocked)-> END               tools <-> agent_capable -> output_shield -> END

The input_shield node calls Llama Guard on the user's message.  If unsafe, it
short-circuits to END with a refusal message.  The output_shield node checks the
agent's completed response and replaces it with a refusal if unsafe.

Shields are active when SAFETY_MODEL is configured; otherwise they are no-ops.
On any safety-model error the check is skipped (fail-open).

The classify node sends the user's message to the fast model with a
prompt listing available tools.  The model replies SIMPLE or COMPLEX.

Two-pass escalation routing:
  - COMPLEX -> agent_capable directly (tool-calling with reliable model)
  - SIMPLE  -> agent_fast first.  If agent_fast produces a text-only
    response, route to output_shield (cheap path).  If agent_fast
    produces tool calls, discard that response and escalate to
    agent_capable for reliable tool execution.

This saves cost on chitchat (fast model handles greetings, FAQs) while
ensuring tool calls are always made by the capable model.

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
    """Graph state extended with model routing, safety, and auth fields."""

    model_tier: str
    safety_blocked: bool
    escalated: bool
    user_role: str
    user_id: str
    tool_allowed_roles: dict[str, list[str]]


def build_routed_graph(
    *,
    system_prompt: str,
    tools: list,
    llms: dict[str, ChatOpenAI],
    tool_descriptions: str,
    tool_allowed_roles: dict[str, list[str]] | None = None,
    checkpointer: Any | None = None,
) -> Any:
    """Build a compiled LangGraph graph with safety shields and two-pass routing.

    Args:
        system_prompt: The agent's system prompt (injected per LLM call).
        tools: LangChain tools available to the agent.
        llms: Mapping of tier name to ChatOpenAI instance.
        tool_descriptions: Human-readable tool descriptions for the classifier prompt.
        tool_allowed_roles: Mapping of tool name to list of allowed role strings.
            When provided, a pre-tool authorization node checks the user's role
            before each tool invocation (RBAC Layer 3).

    Returns:
        A compiled StateGraph with two-pass escalation routing.
    """
    classifier_llm = llms["fast_small"]
    capable_llm = llms["capable_large"]
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

    def after_classify(state: AgentState) -> str:
        """Route to agent_fast for SIMPLE, agent_capable for COMPLEX."""
        tier = state.get("model_tier", "capable_large")
        if tier == "fast_small":
            return "agent_fast"
        return "agent_capable"

    async def agent_fast(state: AgentState) -> dict:
        """First pass with the fast model (tools bound but not trusted).

        If the fast model returns text only, the response is added to
        messages and the graph proceeds to output_shield (cheap path).
        If it attempts tool calls, the response is NOT added to messages
        and the ``escalated`` flag is set so the graph routes to
        agent_capable instead.
        """
        llm = classifier_llm.bind_tools(tools)
        messages = [SystemMessage(content=system_prompt), *state["messages"]]
        response = await llm.ainvoke(messages)

        if response.tool_calls:
            logger.info("Fast model attempted tool calls, escalating to capable_large")
            return {"escalated": True}

        return {"messages": [response]}

    def after_agent_fast(state: AgentState) -> str:
        """Route to agent_capable if fast model tried tool calls."""
        if state.get("escalated"):
            return "agent_capable"
        return "output_shield"

    async def agent_capable(state: AgentState) -> dict:
        """Call the capable LLM with tools bound (reliable tool-calling)."""
        llm = capable_llm.bind_tools(tools)
        messages = [SystemMessage(content=system_prompt), *state["messages"]]
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        """Route to tool_auth (or tools) if the LLM made tool calls, else output shield."""
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tool_auth" if tool_allowed_roles else "tools"
        return "output_shield"

    async def tool_auth(state: AgentState) -> dict:
        """Pre-tool authorization node (RBAC Layer 3).

        Checks each pending tool call against allowed_roles for the user's role.
        Authorized calls proceed; unauthorized calls are replaced with an error
        message back to the agent.
        """
        last = state["messages"][-1]
        if not isinstance(last, AIMessage) or not last.tool_calls:
            return {}

        user_role = state.get("user_role", "")
        user_id = state.get("user_id", "anonymous")
        # Merge graph-level defaults with any per-invocation overrides
        roles_map = {**(tool_allowed_roles or {}), **state.get("tool_allowed_roles", {})}

        blocked: list[str] = []
        for tc in last.tool_calls:
            allowed = roles_map.get(tc["name"])
            if allowed is not None and user_role not in allowed:
                blocked.append(tc["name"])
                logger.warning(
                    "Tool auth DENIED: user=%s role=%s tool=%s allowed=%s",
                    user_id,
                    user_role,
                    tc["name"],
                    allowed,
                )

        if not blocked:
            return {}

        # Return an error message so the agent can inform the user
        denied_list = ", ".join(blocked)
        return {
            "messages": [
                AIMessage(
                    content=f"Tool authorization denied: your role '{user_role}' "
                    f"is not permitted to use: {denied_list}. "
                    "Please let the user know you cannot perform that action."
                )
            ]
        }

    def after_tool_auth(state: AgentState) -> str:
        """Route to tools if auth passed, back to agent if blocked."""
        last = state["messages"][-1]
        # If tool_auth injected an AIMessage (denial), go to output_shield
        if isinstance(last, AIMessage) and not last.tool_calls:
            return "output_shield"
        return "tools"

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
    graph.add_node("agent_fast", agent_fast)
    graph.add_node("agent_capable", agent_capable)
    graph.add_node("tools", tool_node)
    graph.add_node("output_shield", output_shield)

    graph.set_entry_point("input_shield")
    graph.add_conditional_edges(
        "input_shield", after_input_shield, {END: END, "classify": "classify"}
    )
    graph.add_conditional_edges(
        "classify",
        after_classify,
        {"agent_fast": "agent_fast", "agent_capable": "agent_capable"},
    )

    # Fast model path: text-only -> output_shield, tool calls -> agent_capable
    graph.add_conditional_edges(
        "agent_fast",
        after_agent_fast,
        {"output_shield": "output_shield", "agent_capable": "agent_capable"},
    )

    # Capable model path: tool calls -> auth/tools loop, text -> output_shield
    if tool_allowed_roles:
        graph.add_node("tool_auth", tool_auth)
        graph.add_conditional_edges(
            "agent_capable",
            should_continue,
            {"tool_auth": "tool_auth", "output_shield": "output_shield"},
        )
        graph.add_conditional_edges(
            "tool_auth",
            after_tool_auth,
            {"tools": "tools", "output_shield": "output_shield"},
        )
    else:
        graph.add_conditional_edges(
            "agent_capable",
            should_continue,
            {"tools": "tools", "output_shield": "output_shield"},
        )

    graph.add_edge("tools", "agent_capable")
    graph.add_edge("output_shield", END)

    return graph.compile(checkpointer=checkpointer)
