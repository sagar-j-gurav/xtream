"""
LangGraph Agent Nodes
Core agent logic and node functions
"""
from typing import List
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode

from src.agent.state import AgentState
from src.agent.prompts import SYSTEM_PROMPT
from src.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


def create_llm():
    """
    Create and configure the LLM

    Returns:
        ChatOpenAI: Configured LLM instance
    """
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        max_tokens=settings.openai_max_tokens,
        openai_api_key=settings.openai_api_key
    )


async def call_model(state: AgentState) -> AgentState:
    """
    Call the LLM with the current state

    Args:
        state: Current agent state

    Returns:
        AgentState: Updated state with model response
    """
    logger.info("Calling model")

    # Get messages from state
    messages = state["messages"]

    # Filter out ToolMessage instances (they cause OpenAI API errors)
    # Only keep HumanMessage, AIMessage, and SystemMessage
    filtered_messages = [
        msg for msg in messages
        if not isinstance(msg, ToolMessage)
    ]

    # Ensure system message is first
    if not filtered_messages or not isinstance(filtered_messages[0], SystemMessage):
        filtered_messages = [SystemMessage(content=SYSTEM_PROMPT)] + filtered_messages

    # DEBUG: Log the messages being sent to LLM
    logger.info(f"🔍 DEBUG: Sending {len(filtered_messages)} messages to LLM")
    for i, msg in enumerate(filtered_messages):
        msg_type = type(msg).__name__
        content_preview = str(msg.content)[:100] if hasattr(msg, 'content') else "N/A"
        logger.info(f"  Message {i}: {msg_type} - {content_preview}...")

    # Create LLM
    llm = create_llm()

    # Get tools from state metadata if available
    tools = state.get("metadata", {}).get("tools", [])

    logger.info(f"Tools available for binding: {len(tools)}")
    if tools:
        logger.info(f"Tool names: {[t.name for t in tools]}")

        # DEBUG: Log tool details
        for tool in tools:
            logger.info(f"🔧 DEBUG: Tool '{tool.name}' - {tool.description if hasattr(tool, 'description') else 'No description'}")

    # Bind tools to LLM if available
    if tools:
        llm_with_tools = llm.bind_tools(tools)
        response = await llm_with_tools.ainvoke(filtered_messages)
    else:
        logger.warning("No tools available - agent will respond without tools")
        response = await llm.ainvoke(filtered_messages)

    # DEBUG: Log the LLM response details
    has_tool_calls = bool(response.tool_calls) if hasattr(response, 'tool_calls') else False
    logger.info(f"📥 DEBUG: LLM Response - has_tool_calls: {has_tool_calls}")

    if has_tool_calls:
        logger.info(f"🛠️  DEBUG: Tool calls requested: {len(response.tool_calls)}")
        for i, tool_call in enumerate(response.tool_calls):
            logger.info(f"  Tool call {i}: {tool_call.get('name', 'unknown')} with args: {tool_call.get('args', {})}")
    else:
        response_preview = str(response.content)[:200] if hasattr(response, 'content') else "N/A"
        logger.info(f"💬 DEBUG: LLM decided NOT to use tools. Response: {response_preview}...")

    # Update state
    state["messages"] = messages + [response]

    logger.info(
        "Model response generated",
        has_tool_calls=has_tool_calls
    )

    return state


def should_continue(state: AgentState) -> str:
    """
    Determine if the agent should continue to tools or end

    Args:
        state: Current agent state

    Returns:
        str: Next node to execute ("tools" or "end")
    """
    messages = state["messages"]
    last_message = messages[-1] if messages else None

    # DEBUG: Log last message details
    if last_message:
        msg_type = type(last_message).__name__
        has_tool_calls = hasattr(last_message, 'tool_calls') and last_message.tool_calls
        logger.info(f"🔀 DEBUG: Last message type: {msg_type}, has_tool_calls: {has_tool_calls}")

        if has_tool_calls:
            logger.info(f"  Tool calls: {[tc.get('name', 'unknown') for tc in last_message.tool_calls]}")
    else:
        logger.warning("⚠️  DEBUG: No messages in state!")

    # Check if last message has tool calls
    if last_message and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        logger.info("🛠️  DEBUG: Routing to tools", tool_count=len(last_message.tool_calls))
        return "tools"

    logger.info("🏁 DEBUG: Routing to end (no tool calls)")
    return "end"


def create_tool_node(tools: List):
    """
    Create a tool execution node

    Args:
        tools: List of tools to make available

    Returns:
        ToolNode: Configured tool node
    """
    return ToolNode(tools)


async def process_tool_results(state: AgentState) -> AgentState:
    """
    Process tool execution results

    Args:
        state: Current agent state

    Returns:
        AgentState: Updated state
    """
    logger.info("Processing tool results")

    # Tool results are automatically added to messages by ToolNode
    # This node is for any additional processing needed

    return state


async def handle_error(state: AgentState) -> AgentState:
    """
    Handle errors in the agent execution

    Args:
        state: Current agent state

    Returns:
        AgentState: Updated state with error handling
    """
    error = state.get("error")

    if error:
        logger.error(f"Agent error occurred", error=error)

        error_message = AIMessage(
            content="I apologize, but I encountered an error. Please try again or let me know if you need assistance with something else."
        )

        state["messages"] = state["messages"] + [error_message]

    return state
