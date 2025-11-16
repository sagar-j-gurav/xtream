"""
LangGraph Agent Graph
Builds the TESS conversational agent with multi-tool support
"""
from typing import List, Optional
from langgraph.graph import StateGraph, END
from langchain.tools import BaseTool

from src.agent.state import AgentState
from src.agent.nodes import (
    call_model,
    should_continue,
    create_tool_node,
    process_tool_results,
    handle_error
)
from src.tools.chromadb_tool import get_chromadb_search_tool
from src.tools.frappe_mcp import get_all_mcp_tools
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TESSAgent:
    """
    TESS Conversational Agent

    A multi-tool LangGraph agent that autonomously decides when to use:
    - ChromaDB for knowledge base search
    - Frappe MCP tools for lead management
    """

    def __init__(self):
        """Initialize the TESS agent"""
        self.graph = None
        self.tools: List[BaseTool] = []
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the agent graph with all tools

        This method:
        1. Loads ChromaDB search tool
        2. Auto-discovers Frappe MCP tools
        3. Builds the LangGraph workflow
        """
        if self._initialized:
            logger.debug("TESS agent already initialized")
            return

        logger.info("Initializing TESS agent")

        # Load ChromaDB search tool
        chromadb_tool = get_chromadb_search_tool()
        self.tools.append(chromadb_tool)

        # Load MCP tools (auto-discovered from Frappe MCP server)
        try:
            mcp_tools = await get_all_mcp_tools()
            self.tools.extend(mcp_tools)
            logger.info(f"Loaded {len(mcp_tools)} MCP tools from Frappe server")
        except Exception as e:
            logger.warning(
                f"Failed to load MCP tools: {e}. Agent will continue with ChromaDB only."
            )

        logger.info(f"Total tools available: {len(self.tools)}")
        logger.info(f"Tool names: {[tool.name for tool in self.tools]}")

        # Build the graph
        self.graph = self._build_graph()

        self._initialized = True
        logger.info("TESS agent initialized successfully")

    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow

        Returns:
            StateGraph: Compiled agent graph
        """
        logger.info("Building LangGraph workflow")

        # Create the graph
        workflow = StateGraph(AgentState)

        # Create tool node
        tool_node = create_tool_node(self.tools)

        # Add nodes
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)
        workflow.add_node("process_results", process_tool_results)
        workflow.add_node("handle_error", handle_error)

        # Set entry point
        workflow.set_entry_point("agent")

        # Add conditional edges from agent
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                "end": END
            }
        )

        # Add edge from tools back to agent
        workflow.add_edge("tools", "agent")

        # Compile the graph
        compiled_graph = workflow.compile()

        logger.info("LangGraph workflow built successfully")

        return compiled_graph

    async def invoke(
        self,
        message: str,
        session_id: str,
        user_identifier: Optional[str] = None,
        conversation_history: Optional[List] = None
    ) -> str:
        """
        Invoke the agent with a user message

        Args:
            message: User message
            session_id: Session identifier
            user_identifier: User identifier (email, phone, or anonymous)
            conversation_history: Previous conversation messages

        Returns:
            str: Agent response
        """
        if not self._initialized:
            await self.initialize()

        logger.info(
            "Invoking agent",
            session_id=session_id,
            message_preview=message[:100]
        )

        from langchain_core.messages import HumanMessage, SystemMessage
        from src.agent.prompts import SYSTEM_PROMPT

        # Prepare messages
        messages = []

        # Add conversation history if available
        if conversation_history:
            messages.extend(conversation_history)
        else:
            # Add system message
            messages.append(SystemMessage(content=SYSTEM_PROMPT))

        # Add user message
        messages.append(HumanMessage(content=message))

        # Create initial state
        initial_state: AgentState = {
            "messages": messages,
            "session_id": session_id,
            "user_identifier": user_identifier,
            "current_query": message,
            "current_response": None,
            "tool_calls": None,
            "tool_results": None,
            "metadata": {
                "tools": self.tools
            },
            "intent": None,
            "error": None
        }

        try:
            # Invoke the graph
            result = await self.graph.ainvoke(initial_state)

            # Extract final response
            final_messages = result["messages"]
            if final_messages:
                last_message = final_messages[-1]
                response = last_message.content

                logger.info(
                    "Agent invocation completed",
                    session_id=session_id,
                    response_length=len(response)
                )

                return response
            else:
                logger.warning("No response generated by agent")
                return "I apologize, but I couldn't generate a response. Please try again."

        except Exception as e:
            logger.error(
                "Agent invocation failed",
                session_id=session_id,
                error=str(e),
                exc_info=True
            )
            return "I encountered an error while processing your request. Please try again."

    def get_available_tools(self) -> List[str]:
        """
        Get list of available tool names

        Returns:
            List[str]: Tool names
        """
        return [tool.name for tool in self.tools]


# Singleton instance
_tess_agent: Optional[TESSAgent] = None


async def get_tess_agent() -> TESSAgent:
    """
    Get singleton TESS agent instance

    Returns:
        TESSAgent: Initialized TESS agent
    """
    global _tess_agent
    if _tess_agent is None:
        _tess_agent = TESSAgent()
        await _tess_agent.initialize()
    return _tess_agent
