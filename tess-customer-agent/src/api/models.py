"""
API Request/Response Models
Pydantic models for API endpoints
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""

    session_id: str = Field(
        ...,
        description="Unique session identifier",
        min_length=8,
        max_length=64
    )
    message: str = Field(
        ...,
        description="User message",
        min_length=1,
        max_length=5000
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional user identifier (email, phone, or ID)"
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""

    response: str = Field(..., description="Agent response")
    session_id: str = Field(..., description="Session identifier")
    conversation_id: Optional[str] = Field(
        default=None,
        description="Database conversation ID"
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Tools called during this interaction"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Response timestamp"
    )


class MessageItem(BaseModel):
    """Individual message in conversation history"""

    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Message timestamp")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Tool calls made in this message"
    )


class ConversationResponse(BaseModel):
    """Response model for conversation history endpoint"""

    session_id: str = Field(..., description="Session identifier")
    conversation_id: str = Field(..., description="Database conversation ID")
    messages: List[MessageItem] = Field(..., description="Conversation messages")
    created_at: str = Field(..., description="Conversation creation timestamp")
    message_count: int = Field(..., description="Total number of messages")


class IndexDocumentRequest(BaseModel):
    """Request model for indexing documents"""

    documents: List[str] = Field(
        ...,
        description="List of document texts to index",
        min_length=1
    )
    metadatas: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional metadata for each document"
    )


class IndexDocumentResponse(BaseModel):
    """Response model for document indexing"""

    indexed: int = Field(..., description="Number of documents indexed")
    collection: str = Field(..., description="Collection name")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Index timestamp"
    )


class HealthResponse(BaseModel):
    """Response model for health check"""

    status: str = Field(..., description="Service status")
    version: str = Field(default="1.0.0", description="API version")
    environment: str = Field(..., description="Environment (dev/uat/prod)")
    services: Dict[str, str] = Field(..., description="Status of dependent services")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Health check timestamp"
    )


class ErrorResponse(BaseModel):
    """Error response model"""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Error details")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Error timestamp"
    )
