"""
LangGraph Agent State Schema
Defines the state structure for TESS agent
"""
from typing import TypedDict, List, Optional, Dict, Any, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    State schema for TESS agent

    This defines the structure of data that flows through
    the LangGraph agent nodes
    """

    # Conversation messages (annotated with add_messages reducer to append rather than replace)
    messages: Annotated[List[BaseMessage], add_messages]

    # Session information
    session_id: str
    user_identifier: Optional[str]

    # Current query and response
    current_query: Optional[str]
    current_response: Optional[str]

    # Tool execution tracking
    tool_calls: Optional[List[Dict[str, Any]]]
    tool_results: Optional[List[Dict[str, Any]]]

    # Conversation metadata
    metadata: Optional[Dict[str, Any]]

    # Intent classification
    intent: Optional[str]

    # Error tracking
    error: Optional[str]
