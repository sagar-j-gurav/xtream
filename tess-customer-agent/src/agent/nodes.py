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

    # Create LLM
    llm = create_llm()

    # Get tools from state metadata if available
    tools = state.get("metadata", {}).get("tools", [])

    logger.info(f"Tools available for binding: {len(tools)}")
    if tools:
        logger.info(f"Tool names: {[t.name for t in tools]}")

    # Bind tools to LLM if available
    if tools:
        llm_with_tools = llm.bind_tools(tools)
        response = await llm_with_tools.ainvoke(filtered_messages)
    else:
        logger.warning("No tools available - agent will respond without tools")
        response = await llm.ainvoke(filtered_messages)

    # Update state
    state["messages"] = messages + [response]

    logger.info(
        "Model response generated",
        has_tool_calls=bool(response.tool_calls) if hasattr(response, 'tool_calls') else False
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

    # Check if last message has tool calls
    if last_message and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        logger.info("Routing to tools", tool_count=len(last_message.tool_calls))
        return "tools"

    logger.info("Routing to end")
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
