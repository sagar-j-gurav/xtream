"""
Embedding utilities for TESS
OpenAI text embeddings wrapper
"""
from typing import List
from langchain_openai import OpenAIEmbeddings

from src.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TESSEmbeddings:
    """Wrapper for OpenAI embeddings"""

    def __init__(self):
        """Initialize embeddings"""
        self.settings = get_settings()
        self.embeddings = OpenAIEmbeddings(
            model=self.settings.openai_embedding_model,
            openai_api_key=self.settings.openai_api_key
        )
        logger.info(
            f"Initialized embeddings with model: {self.settings.openai_embedding_model}"
        )

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents

        Args:
            texts: List of text documents

        Returns:
            List[List[float]]: List of embeddings
        """
        logger.debug(f"Embedding {len(texts)} documents")
        embeddings = await self.embeddings.aembed_documents(texts)
        return embeddings

    async def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query

        Args:
            text: Query text

        Returns:
            List[float]: Embedding vector
        """
        logger.debug("Embedding query")
        embedding = await self.embeddings.aembed_query(text)
        return embedding


# Singleton instance
_embeddings_instance: TESSEmbeddings = None


def get_embeddings() -> TESSEmbeddings:
    """
    Get singleton embeddings instance

    Returns:
        TESSEmbeddings: Embeddings instance
    """
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = TESSEmbeddings()
    return _embeddings_instance
