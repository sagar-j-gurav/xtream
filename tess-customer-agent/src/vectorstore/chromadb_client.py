"""
ChromaDB Client for TESS
Vector store for knowledge base search
"""
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import os

from src.config.settings import get_settings
from src.config.constants import CHUNK_SIZE, CHUNK_OVERLAP
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ChromaDBClient:
    """Client for ChromaDB vector store"""

    def __init__(self):
        """Initialize ChromaDB client"""
        self.settings = get_settings()
        self.client = None
        self.collection = None
        self.embedding_function = None

    def initialize(self) -> None:
        """Initialize ChromaDB client and collection"""
        if self.client is not None:
            logger.debug("ChromaDB client already initialized")
            return

        # Create persist directory if it doesn't exist
        persist_dir = self.settings.chroma_persist_dir
        os.makedirs(persist_dir, exist_ok=True)

        # Initialize ChromaDB client with persistent storage
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Initialize OpenAI embedding function
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.settings.openai_api_key,
            model_name=self.settings.openai_embedding_model
        )

        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name=self.settings.chroma_collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(
                f"Loaded existing collection: {self.settings.chroma_collection_name}"
            )
        except Exception:
            self.collection = self.client.create_collection(
                name=self.settings.chroma_collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "TESS knowledge base"}
            )
            logger.info(
                f"Created new collection: {self.settings.chroma_collection_name}"
            )

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """
        Add documents to the vector store

        Args:
            documents: List of document texts
            metadatas: List of metadata dictionaries
            ids: List of document IDs (auto-generated if not provided)
        """
        if not self.collection:
            self.initialize()

        # Generate IDs if not provided
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in documents]

        # Add documents
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        logger.info(f"Added {len(documents)} documents to collection")

    def search(
        self,
        query: str,
        n_results: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents

        Args:
            query: Search query
            n_results: Number of results to return (default from settings)
            filters: Metadata filters

        Returns:
            List[Dict[str, Any]]: Search results with documents and metadata
        """
        if not self.collection:
            self.initialize()

        n_results = n_results or self.settings.chroma_top_k

        # Perform search
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=filters
        )

        # Format results
        formatted_results = []
        if results['documents'] and len(results['documents']) > 0:
            for i, doc in enumerate(results['documents'][0]):
                # Check similarity threshold
                distance = results['distances'][0][i] if results['distances'] else 0
                similarity = 1 - distance  # Convert distance to similarity

                if similarity >= self.settings.chroma_similarity_threshold:
                    formatted_results.append({
                        'document': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'similarity': similarity,
                        'id': results['ids'][0][i]
                    })

        logger.info(
            f"Search returned {len(formatted_results)} results above threshold",
            query=query[:50]
        )

        return formatted_results

    def delete_collection(self) -> None:
        """Delete the collection (use with caution)"""
        if not self.client:
            self.initialize()

        self.client.delete_collection(name=self.settings.chroma_collection_name)
        logger.warning(f"Deleted collection: {self.settings.chroma_collection_name}")
        self.collection = None

    def count_documents(self) -> int:
        """
        Get the number of documents in the collection

        Returns:
            int: Document count
        """
        if not self.collection:
            self.initialize()

        count = self.collection.count()
        return count

    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get collection information

        Returns:
            Dict[str, Any]: Collection metadata
        """
        if not self.collection:
            self.initialize()

        return {
            'name': self.collection.name,
            'count': self.collection.count(),
            'metadata': self.collection.metadata
        }


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks

    Args:
        text: Text to chunk
        chunk_size: Size of each chunk in characters
        overlap: Overlap between chunks

    Returns:
        List[str]: List of text chunks
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)

            if break_point > chunk_size * 0.5:  # Only break if we're past halfway
                chunk = chunk[:break_point + 1]
                end = start + len(chunk)

        chunks.append(chunk.strip())
        start = end - overlap

    return chunks


# Singleton instance
_chroma_client: Optional[ChromaDBClient] = None


def get_chroma_client() -> ChromaDBClient:
    """
    Get singleton ChromaDB client instance

    Returns:
        ChromaDBClient: ChromaDB client
    """
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = ChromaDBClient()
        _chroma_client.initialize()
    return _chroma_client
