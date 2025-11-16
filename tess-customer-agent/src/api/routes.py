"""
API Routes for TESS
FastAPI route handlers
"""
from typing import List
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from src.api.models import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    IndexDocumentRequest,
    IndexDocumentResponse,
    HealthResponse,
    ErrorResponse,
    MessageItem
)
from src.agent.graph import get_tess_agent
from src.memory.postgres_manager import get_memory_manager
from src.memory.checkpointer import (
    load_conversation_history,
    save_message_to_history
)
from src.tools.chromadb_tool import index_documents_from_files
from src.vectorstore.chromadb_client import get_chroma_client
from src.config.settings import get_settings
from src.config.constants import API_V1_PREFIX
from src.utils.logging import get_logger
from src.utils.validators import is_valid_session_id

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix=API_V1_PREFIX)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat with TESS agent

    Args:
        request: Chat request

    Returns:
        ChatResponse: Agent response
    """
    try:
        logger.info(
            "Processing chat request",
            session_id=request.session_id,
            user_id=request.user_id
        )

        # Validate session ID
        if not is_valid_session_id(request.session_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session ID format"
            )

        # Get agent
        agent = await get_tess_agent()

        # Load conversation history
        conversation_history = await load_conversation_history(
            request.session_id,
            max_messages=get_settings().max_conversation_history
        )

        # Get agent response
        response_text = await agent.invoke(
            message=request.message,
            session_id=request.session_id,
            user_identifier=request.user_id,
            conversation_history=conversation_history
        )

        # Save user message and agent response to memory
        from langchain_core.messages import HumanMessage, AIMessage

        await save_message_to_history(
            session_id=request.session_id,
            message=HumanMessage(content=request.message),
            user_identifier=request.user_id
        )

        await save_message_to_history(
            session_id=request.session_id,
            message=AIMessage(content=response_text),
            user_identifier=request.user_id
        )

        # Get conversation ID
        memory_manager = get_memory_manager()
        conversation_id = await memory_manager.get_conversation_id(request.session_id)

        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
            conversation_id=conversation_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Chat request failed",
            session_id=request.session_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat request"
        )


@router.get("/conversations/{session_id}", response_model=ConversationResponse)
async def get_conversation(session_id: str) -> ConversationResponse:
    """
    Get conversation history

    Args:
        session_id: Session identifier

    Returns:
        ConversationResponse: Conversation history
    """
    try:
        logger.info("Fetching conversation", session_id=session_id)

        # Validate session ID
        if not is_valid_session_id(session_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session ID format"
            )

        # Get memory manager
        memory_manager = get_memory_manager()
        await memory_manager.initialize()

        # Get conversation ID
        conversation_id = await memory_manager.get_conversation_id(session_id)

        if not conversation_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Get messages
        messages_data = await memory_manager.get_conversation_messages(conversation_id)

        # Convert to MessageItem models
        messages = [
            MessageItem(
                role=msg['role'],
                content=msg['content'],
                timestamp=msg['timestamp'],
                tool_calls=msg.get('tool_calls')
            )
            for msg in messages_data
        ]

        # Get conversation metadata (we'll use first message timestamp as created_at)
        created_at = messages[0].timestamp if messages else ""

        return ConversationResponse(
            session_id=session_id,
            conversation_id=conversation_id,
            messages=messages,
            created_at=created_at,
            message_count=len(messages)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to fetch conversation",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch conversation"
        )


@router.post("/index-knowledge", response_model=IndexDocumentResponse)
async def index_knowledge(request: IndexDocumentRequest) -> IndexDocumentResponse:
    """
    Index documents into knowledge base

    Args:
        request: Index request

    Returns:
        IndexDocumentResponse: Indexing result
    """
    try:
        logger.info(f"Indexing {len(request.documents)} documents")

        # Get ChromaDB client
        chroma_client = get_chroma_client()

        # Add documents
        chroma_client.add_documents(
            documents=request.documents,
            metadatas=request.metadatas
        )

        return IndexDocumentResponse(
            indexed=len(request.documents),
            collection=get_settings().chroma_collection_name
        )

    except Exception as e:
        logger.error(
            "Failed to index documents",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to index documents"
        )


@router.get("/users/{user_id}/conversations")
async def get_user_conversations(
    user_id: str,
    limit: int = 100,
    offset: int = 0
):
    """
    Get all conversations for a user

    Args:
        user_id: User identifier (email, phone, or ID)
        limit: Maximum number of conversations
        offset: Pagination offset

    Returns:
        List of conversations with metadata
    """
    try:
        logger.info(f"Fetching conversations for user: {user_id}")

        memory_manager = get_memory_manager()
        await memory_manager.initialize()

        conversations = await memory_manager.get_conversations_by_user(
            user_identifier=user_id,
            limit=limit,
            offset=offset
        )

        return {
            "user_id": user_id,
            "conversations": conversations,
            "count": len(conversations),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Failed to fetch user conversations", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user conversations"
        )


@router.get("/users/{user_id}/messages")
async def get_user_messages(
    user_id: str,
    limit: int = 1000,
    offset: int = 0
):
    """
    Get all messages across all conversations for a user

    Args:
        user_id: User identifier (email, phone, or ID)
        limit: Maximum number of messages
        offset: Pagination offset

    Returns:
        List of messages with conversation context
    """
    try:
        logger.info(f"Fetching messages for user: {user_id}")

        memory_manager = get_memory_manager()
        await memory_manager.initialize()

        messages = await memory_manager.get_all_messages_by_user(
            user_identifier=user_id,
            limit=limit,
            offset=offset
        )

        return {
            "user_id": user_id,
            "messages": messages,
            "count": len(messages),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Failed to fetch user messages", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user messages"
        )


@router.get("/users/{user_id}/queries")
async def get_user_queries(
    user_id: str,
    limit: int = 100
):
    """
    Get user's query history (only user messages, not assistant responses)

    Args:
        user_id: User identifier (email, phone, or ID)
        limit: Maximum number of queries

    Returns:
        List of user queries
    """
    try:
        logger.info(f"Fetching query history for user: {user_id}")

        memory_manager = get_memory_manager()
        await memory_manager.initialize()

        queries = await memory_manager.get_user_query_history(
            user_identifier=user_id,
            limit=limit
        )

        return {
            "user_id": user_id,
            "queries": queries,
            "count": len(queries),
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Failed to fetch user queries", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user queries"
        )


@router.post("/knowledge/upload-faqs")
async def upload_faqs(faqs: List[Dict[str, str]], source: str = "api_upload"):
    """
    Upload FAQ data to knowledge base

    Request body:
    [
        {
            "question": "What is your refund policy?",
            "answer": "We offer 30-day refunds...",
            "category": "policies"  # optional
        },
        ...
    ]

    Args:
        faqs: List of FAQ dictionaries
        source: Source identifier

    Returns:
        Number of FAQs indexed
    """
    try:
        logger.info(f"Uploading {len(faqs)} FAQs")

        from src.vectorstore.chunking import index_faqs

        indexed_count = await index_faqs(faqs=faqs, source=source)

        return {
            "indexed": indexed_count,
            "source": source,
            "type": "faq"
        }

    except Exception as e:
        logger.error(f"Failed to upload FAQs", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload FAQs"
        )


@router.post("/knowledge/upload-content")
async def upload_website_content(
    content: str,
    url: str,
    page_title: str = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
):
    """
    Upload website content to knowledge base

    Args:
        content: Website content (HTML stripped)
        url: Source URL
        page_title: Optional page title
        chunk_size: Chunk size in characters
        chunk_overlap: Overlap between chunks

    Returns:
        Number of chunks indexed
    """
    try:
        logger.info(f"Uploading website content from {url}")

        from src.vectorstore.chunking import index_website_content

        indexed_count = await index_website_content(
            content=content,
            url=url,
            page_title=page_title,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        return {
            "indexed": indexed_count,
            "source": url,
            "type": "website_content",
            "chunk_size": chunk_size
        }

    except Exception as e:
        logger.error(f"Failed to upload website content", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload website content"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint

    Returns:
        HealthResponse: Service health status
    """
    settings = get_settings()
    services = {}

    # Check PostgreSQL
    try:
        memory_manager = get_memory_manager()
        await memory_manager.initialize()
        services["postgresql"] = "healthy"
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")
        services["postgresql"] = "unhealthy"

    # Check ChromaDB
    try:
        chroma_client = get_chroma_client()
        chroma_client.count_documents()
        services["chromadb"] = "healthy"
    except Exception as e:
        logger.error(f"ChromaDB health check failed: {e}")
        services["chromadb"] = "unhealthy"

    # Check agent
    try:
        agent = await get_tess_agent()
        services["agent"] = "healthy"
    except Exception as e:
        logger.error(f"Agent health check failed: {e}")
        services["agent"] = "unhealthy"

    # Overall status
    overall_status = "healthy" if all(
        status == "healthy" for status in services.values()
    ) else "degraded"

    return HealthResponse(
        status=overall_status,
        environment=settings.app_env,
        services=services
    )
