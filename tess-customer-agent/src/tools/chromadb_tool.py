"""
ChromaDB Knowledge Search Tool
Semantic search tool for TESS knowledge base
"""
from typing import Dict, Any, Optional, List
from langchain.tools import Tool
from pydantic import BaseModel, Field

from src.vectorstore.chromadb_client import get_chroma_client
from src.config.constants import TOOL_CHROMADB
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SearchKnowledgeBaseInput(BaseModel):
    """Input schema for search_knowledge_base tool"""

    query: str = Field(
        description="The search query to find relevant information in the knowledge base"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata filters to narrow down search (e.g., {'category': 'products'})"
    )


async def search_knowledge_base(
    query: str,
    filters: Optional[Dict[str, Any]] = None
) -> str:
    """
    Search the knowledge base for relevant information

    Args:
        query: Search query
        filters: Optional metadata filters

    Returns:
        str: Formatted search results with source documents
    """
    logger.info("🔎 DEBUG: search_knowledge_base TOOL CALLED!")
    logger.info(f"🔎 DEBUG: Query: '{query}'")
    logger.info(f"🔎 DEBUG: Filters: {filters}")

    try:
        # Get ChromaDB client
        chroma_client = get_chroma_client()

        # DEBUG: Check collection status
        try:
            doc_count = chroma_client.count_documents()
            logger.info(f"📊 DEBUG: ChromaDB collection has {doc_count} documents")
        except Exception as e:
            logger.warning(f"⚠️  DEBUG: Could not get document count: {e}")

        # Perform search
        results = chroma_client.search(
            query=query,
            filters=filters
        )

        logger.info(f"📊 DEBUG: Search returned {len(results) if results else 0} results")

        if not results:
            logger.info("❌ DEBUG: No results found in knowledge base")
            return (
                "I couldn't find specific information about that in my knowledge base. "
                "Could you rephrase your question or provide more details?"
            )

        # DEBUG: Log result details
        for i, result in enumerate(results[:3], 1):  # Log first 3 results
            doc_preview = result['document'][:100]
            similarity = result['similarity']
            logger.info(f"  Result {i}: similarity={similarity:.3f}, content='{doc_preview}...'")

        # Format results
        formatted_response = "Based on my knowledge base, here's what I found:\n\n"

        for i, result in enumerate(results, 1):
            document = result['document']
            similarity = result['similarity']
            metadata = result.get('metadata', {})

            formatted_response += f"{i}. {document}\n"

            # Add source information if available
            if metadata:
                source = metadata.get('source', '')
                if source:
                    formatted_response += f"   (Source: {source})\n"

            formatted_response += "\n"

        logger.info(f"✅ DEBUG: Knowledge base search completed with {len(results)} results")

        return formatted_response.strip()

    except Exception as e:
        logger.error(f"❌ DEBUG: Knowledge base search FAILED", error=str(e), exc_info=True)
        return (
            "I encountered an error while searching my knowledge base. "
            "Please try again or let me know if you need assistance with something else."
        )


def get_chromadb_search_tool() -> Tool:
    """
    Create the ChromaDB search tool for LangChain

    Returns:
        Tool: LangChain tool for knowledge base search
    """
    return Tool(
        name=TOOL_CHROMADB,
        description=(
            "Search the knowledge base for information about products, services, "
            "features, policies, documentation, and FAQs. "
            "Use this tool when the user asks about product information, "
            "how things work, pricing, policies, or general support questions. "
            "Input should be a clear search query."
        ),
        func=lambda query: search_knowledge_base(query),
        coroutine=search_knowledge_base,
        args_schema=SearchKnowledgeBaseInput
    )


async def index_documents_from_files(
    file_paths: List[str],
    metadata_list: Optional[List[Dict[str, Any]]] = None
) -> int:
    """
    Index documents from files into ChromaDB

    Args:
        file_paths: List of file paths to index
        metadata_list: Optional list of metadata dictionaries for each file

    Returns:
        int: Number of documents indexed
    """
    from src.vectorstore.chromadb_client import chunk_text

    chroma_client = get_chroma_client()
    total_chunks = 0

    for i, file_path in enumerate(file_paths):
        logger.info(f"Indexing file: {file_path}")

        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Chunk the document
            chunks = chunk_text(content)

            # Prepare metadata
            metadata = metadata_list[i] if metadata_list and i < len(metadata_list) else {}
            metadata['source'] = file_path

            # Create metadata for each chunk
            chunk_metadata = [
                {**metadata, 'chunk_index': j}
                for j in range(len(chunks))
            ]

            # Add to ChromaDB
            chroma_client.add_documents(
                documents=chunks,
                metadatas=chunk_metadata
            )

            total_chunks += len(chunks)
            logger.info(f"Indexed {len(chunks)} chunks from {file_path}")

        except Exception as e:
            logger.error(f"Failed to index {file_path}", error=str(e))

    logger.info(f"Total indexed: {total_chunks} chunks from {len(file_paths)} files")
    return total_chunks
