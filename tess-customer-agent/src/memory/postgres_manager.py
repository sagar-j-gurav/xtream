"""
PostgreSQL Memory Manager for TESS
Manages conversation history and state in PostgreSQL
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncpg
from asyncpg.pool import Pool
import json

from src.config.settings import get_settings
from src.config.constants import (
    ROLE_USER,
    ROLE_ASSISTANT,
    ROLE_SYSTEM,
    SESSION_ID_LENGTH
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class PostgresMemoryManager:
    """Manages conversation memory in PostgreSQL"""

    def __init__(self):
        """Initialize the memory manager"""
        self.settings = get_settings()
        self.pool: Optional[Pool] = None

    async def initialize(self) -> None:
        """Initialize database connection pool"""
        if self.pool is None:
            logger.info("Initializing PostgreSQL connection pool")
            self.pool = await asyncpg.create_pool(
                host=self.settings.postgres_host,
                port=self.settings.postgres_port,
                user=self.settings.postgres_user,
                password=self.settings.postgres_password,
                database=self.settings.postgres_db,
                min_size=2,
                max_size=self.settings.postgres_pool_size,
            )
            logger.info("PostgreSQL connection pool initialized")

    async def close(self) -> None:
        """Close database connection pool"""
        if self.pool:
            logger.info("Closing PostgreSQL connection pool")
            await self.pool.close()
            self.pool = None

    async def create_conversation(
        self,
        session_id: str,
        user_identifier: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new conversation

        Args:
            session_id: Unique session identifier
            user_identifier: User email, phone, or anonymous ID
            metadata: Additional conversation metadata

        Returns:
            str: Conversation ID
        """
        if not self.pool:
            await self.initialize()

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO conversations (session_id, user_identifier, metadata)
                VALUES ($1, $2, $3)
                ON CONFLICT (session_id) DO UPDATE SET updated_at = NOW()
                RETURNING id
                """,
                session_id,
                user_identifier,
                json.dumps(metadata or {})
            )
            conversation_id = str(row['id'])
            logger.info(
                "Created conversation",
                conversation_id=conversation_id,
                session_id=session_id
            )
            return conversation_id

    async def get_conversation_id(self, session_id: str) -> Optional[str]:
        """
        Get conversation ID by session ID

        Args:
            session_id: Session identifier

        Returns:
            Optional[str]: Conversation ID or None if not found
        """
        if not self.pool:
            await self.initialize()

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM conversations WHERE session_id = $1",
                session_id
            )
            return str(row['id']) if row else None

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tokens_used: Optional[int] = None
    ) -> str:
        """
        Add a message to the conversation

        Args:
            conversation_id: Conversation ID
            role: Message role (user, assistant, system)
            content: Message content
            tool_calls: List of tool calls made
            tokens_used: Number of tokens used

        Returns:
            str: Message ID
        """
        if not self.pool:
            await self.initialize()

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO messages (conversation_id, role, content, tool_calls, tokens_used)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                conversation_id,
                role,
                content,
                json.dumps(tool_calls) if tool_calls else None,
                tokens_used
            )
            message_id = str(row['id'])
            logger.debug(
                "Added message",
                message_id=message_id,
                conversation_id=conversation_id,
                role=role
            )
            return message_id

    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a conversation

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to retrieve
            offset: Number of messages to skip

        Returns:
            List[Dict[str, Any]]: List of messages
        """
        if not self.pool:
            await self.initialize()

        query = """
            SELECT id, role, content, tool_calls, timestamp, tokens_used
            FROM messages
            WHERE conversation_id = $1
            ORDER BY timestamp ASC
        """

        params = [conversation_id]

        if limit:
            query += f" LIMIT ${len(params) + 1}"
            params.append(limit)

        if offset:
            query += f" OFFSET ${len(params) + 1}"
            params.append(offset)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            messages = [
                {
                    'id': str(row['id']),
                    'role': row['role'],
                    'content': row['content'],
                    'tool_calls': json.loads(row['tool_calls']) if row['tool_calls'] else None,
                    'timestamp': row['timestamp'].isoformat(),
                    'tokens_used': row['tokens_used']
                }
                for row in rows
            ]
            return messages

    async def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent messages for a session

        Args:
            session_id: Session identifier
            limit: Number of recent messages to retrieve

        Returns:
            List[Dict[str, Any]]: List of recent messages
        """
        conversation_id = await self.get_conversation_id(session_id)
        if not conversation_id:
            return []

        if not self.pool:
            await self.initialize()

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, role, content, tool_calls, timestamp, tokens_used
                FROM messages
                WHERE conversation_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
                """,
                conversation_id,
                limit
            )
            # Reverse to get chronological order
            messages = [
                {
                    'id': str(row['id']),
                    'role': row['role'],
                    'content': row['content'],
                    'tool_calls': json.loads(row['tool_calls']) if row['tool_calls'] else None,
                    'timestamp': row['timestamp'].isoformat(),
                    'tokens_used': row['tokens_used']
                }
                for row in reversed(rows)
            ]
            return messages

    async def get_message_count(self, conversation_id: str) -> int:
        """
        Get total message count for a conversation

        Args:
            conversation_id: Conversation ID

        Returns:
            int: Message count
        """
        if not self.pool:
            await self.initialize()

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT COUNT(*) as count FROM messages WHERE conversation_id = $1",
                conversation_id
            )
            return row['count']

    async def create_summary(
        self,
        conversation_id: str,
        summary: str,
        message_count: int
    ) -> str:
        """
        Create a conversation summary

        Args:
            conversation_id: Conversation ID
            summary: Summary text
            message_count: Number of messages summarized

        Returns:
            str: Summary ID
        """
        if not self.pool:
            await self.initialize()

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO conversation_summaries (conversation_id, summary, message_count)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                conversation_id,
                summary,
                message_count
            )
            summary_id = str(row['id'])
            logger.info(
                "Created conversation summary",
                summary_id=summary_id,
                conversation_id=conversation_id,
                message_count=message_count
            )
            return summary_id

    async def get_latest_summary(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest summary for a conversation

        Args:
            conversation_id: Conversation ID

        Returns:
            Optional[Dict[str, Any]]: Summary data or None
        """
        if not self.pool:
            await self.initialize()

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, summary, message_count, created_at
                FROM conversation_summaries
                WHERE conversation_id = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                conversation_id
            )
            if row:
                return {
                    'id': str(row['id']),
                    'summary': row['summary'],
                    'message_count': row['message_count'],
                    'created_at': row['created_at'].isoformat()
                }
            return None

    async def delete_old_conversations(self, days: int = 90) -> int:
        """
        Archive conversations older than specified days

        Args:
            days: Age threshold in days

        Returns:
            int: Number of conversations archived
        """
        if not self.pool:
            await self.initialize()

        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT archive_old_conversations($1)",
                days
            )
            logger.info(f"Archived {result} old conversations")
            return result

    async def get_conversations_by_user(
        self,
        user_identifier: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all conversations for a user

        Args:
            user_identifier: User email, phone, or ID
            limit: Maximum number of conversations
            offset: Number of conversations to skip

        Returns:
            List[Dict[str, Any]]: List of conversations
        """
        if not self.pool:
            await self.initialize()

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    c.id,
                    c.session_id,
                    c.user_identifier,
                    c.created_at,
                    c.updated_at,
                    c.metadata,
                    COUNT(m.id) as message_count,
                    MAX(m.timestamp) as last_message_at
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_identifier = $1
                GROUP BY c.id, c.session_id, c.user_identifier, c.created_at, c.updated_at, c.metadata
                ORDER BY c.updated_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_identifier,
                limit,
                offset
            )

            conversations = [
                {
                    'conversation_id': str(row['id']),
                    'session_id': row['session_id'],
                    'user_identifier': row['user_identifier'],
                    'created_at': row['created_at'].isoformat(),
                    'updated_at': row['updated_at'].isoformat(),
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'message_count': row['message_count'],
                    'last_message_at': row['last_message_at'].isoformat() if row['last_message_at'] else None
                }
                for row in rows
            ]

            return conversations

    async def get_all_messages_by_user(
        self,
        user_identifier: str,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all messages across all conversations for a user

        Args:
            user_identifier: User email, phone, or ID
            limit: Maximum number of messages
            offset: Number of messages to skip

        Returns:
            List[Dict[str, Any]]: List of messages with conversation context
        """
        if not self.pool:
            await self.initialize()

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    m.id,
                    m.conversation_id,
                    c.session_id,
                    m.role,
                    m.content,
                    m.tool_calls,
                    m.timestamp,
                    m.tokens_used
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.user_identifier = $1
                ORDER BY m.timestamp DESC
                LIMIT $2 OFFSET $3
                """,
                user_identifier,
                limit,
                offset
            )

            messages = [
                {
                    'message_id': str(row['id']),
                    'conversation_id': str(row['conversation_id']),
                    'session_id': row['session_id'],
                    'role': row['role'],
                    'content': row['content'],
                    'tool_calls': json.loads(row['tool_calls']) if row['tool_calls'] else None,
                    'timestamp': row['timestamp'].isoformat(),
                    'tokens_used': row['tokens_used']
                }
                for row in rows
            ]

            return messages

    async def get_user_query_history(
        self,
        user_identifier: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get only user queries (not assistant responses) for analysis

        Args:
            user_identifier: User email, phone, or ID
            limit: Maximum number of queries

        Returns:
            List[Dict[str, Any]]: List of user queries
        """
        if not self.pool:
            await self.initialize()

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    m.id,
                    m.conversation_id,
                    c.session_id,
                    m.content,
                    m.timestamp
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.user_identifier = $1 AND m.role = 'user'
                ORDER BY m.timestamp DESC
                LIMIT $2
                """,
                user_identifier,
                limit
            )

            queries = [
                {
                    'message_id': str(row['id']),
                    'conversation_id': str(row['conversation_id']),
                    'session_id': row['session_id'],
                    'query': row['content'],
                    'timestamp': row['timestamp'].isoformat()
                }
                for row in rows
            ]

            return queries


# Singleton instance
_memory_manager: Optional[PostgresMemoryManager] = None


def get_memory_manager() -> PostgresMemoryManager:
    """
    Get singleton instance of PostgresMemoryManager

    Returns:
        PostgresMemoryManager: Memory manager instance
    """
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = PostgresMemoryManager()
    return _memory_manager
