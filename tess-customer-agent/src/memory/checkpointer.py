"""
LangGraph Checkpointer for PostgreSQL
Integrates PostgreSQL memory with LangGraph state persistence
"""
from typing import Optional, Dict, Any, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver

from src.memory.postgres_manager import get_memory_manager
from src.config.constants import ROLE_USER, ROLE_ASSISTANT, ROLE_SYSTEM
from src.utils.logging import get_logger

logger = get_logger(__name__)


def message_to_role(message: BaseMessage) -> str:
    """
    Convert LangChain message to role string

    Args:
        message: LangChain message

    Returns:
        str: Role string
    """
    if isinstance(message, HumanMessage):
        return ROLE_USER
    elif isinstance(message, AIMessage):
        return ROLE_ASSISTANT
    elif isinstance(message, SystemMessage):
        return ROLE_SYSTEM
    else:
        return "assistant"


def role_to_message(role: str, content: str) -> BaseMessage:
    """
    Convert role string to LangChain message

    Args:
        role: Role string
        content: Message content

    Returns:
        BaseMessage: LangChain message
    """
    if role == ROLE_USER:
        return HumanMessage(content=content)
    elif role == ROLE_ASSISTANT:
        return AIMessage(content=content)
    elif role == ROLE_SYSTEM:
        return SystemMessage(content=content)
    else:
        return AIMessage(content=content)


async def load_conversation_history(
    session_id: str,
    max_messages: int = 10
) -> List[BaseMessage]:
    """
    Load conversation history from PostgreSQL

    Args:
        session_id: Session identifier
        max_messages: Maximum number of messages to load

    Returns:
        List[BaseMessage]: List of messages
    """
    memory_manager = get_memory_manager()
    await memory_manager.initialize()

    # Get or create conversation
    conversation_id = await memory_manager.get_conversation_id(session_id)

    if not conversation_id:
        logger.info(f"No existing conversation found for session {session_id}")
        return []

    # Get recent messages
    messages_data = await memory_manager.get_recent_messages(
        session_id,
        limit=max_messages
    )

    # Convert to LangChain messages
    messages = [
        role_to_message(msg['role'], msg['content'])
        for msg in messages_data
    ]

    logger.info(
        f"Loaded {len(messages)} messages from conversation history",
        session_id=session_id
    )

    return messages


async def save_message_to_history(
    session_id: str,
    message: BaseMessage,
    user_identifier: Optional[str] = None
) -> None:
    """
    Save a message to conversation history

    Args:
        session_id: Session identifier
        message: Message to save
        user_identifier: User identifier (email, phone, or anonymous ID)
    """
    memory_manager = get_memory_manager()
    await memory_manager.initialize()

    # Get or create conversation
    conversation_id = await memory_manager.get_conversation_id(session_id)

    if not conversation_id:
        conversation_id = await memory_manager.create_conversation(
            session_id=session_id,
            user_identifier=user_identifier
        )

    # Extract role and content
    role = message_to_role(message)
    content = message.content

    # Save message
    await memory_manager.add_message(
        conversation_id=conversation_id,
        role=role,
        content=content
    )

    logger.debug(
        f"Saved message to history",
        session_id=session_id,
        role=role
    )


async def should_summarize_conversation(session_id: str, threshold: int = 15) -> bool:
    """
    Check if conversation should be summarized

    Args:
        session_id: Session identifier
        threshold: Message count threshold for summarization

    Returns:
        bool: True if should summarize, False otherwise
    """
    memory_manager = get_memory_manager()
    await memory_manager.initialize()

    conversation_id = await memory_manager.get_conversation_id(session_id)
    if not conversation_id:
        return False

    message_count = await memory_manager.get_message_count(conversation_id)
    return message_count >= threshold


async def create_conversation_summary(
    session_id: str,
    summary_text: str
) -> None:
    """
    Create a summary for the conversation

    Args:
        session_id: Session identifier
        summary_text: Summary text
    """
    memory_manager = get_memory_manager()
    await memory_manager.initialize()

    conversation_id = await memory_manager.get_conversation_id(session_id)
    if not conversation_id:
        logger.warning(f"Cannot create summary: conversation not found for {session_id}")
        return

    message_count = await memory_manager.get_message_count(conversation_id)

    await memory_manager.create_summary(
        conversation_id=conversation_id,
        summary=summary_text,
        message_count=message_count
    )

    logger.info(
        f"Created conversation summary",
        session_id=session_id,
        message_count=message_count
    )
