"""
Base Tool Class for TESS
Common functionality for all tools
"""
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from src.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BaseTool(ABC):
    """Base class for TESS tools"""

    def __init__(self, name: str, description: str):
        """
        Initialize base tool

        Args:
            name: Tool name
            description: Tool description
        """
        self.name = name
        self.description = description
        self.settings = get_settings()

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Execute the tool

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            Any: Tool execution result
        """
        pass

    def get_retry_decorator(self):
        """
        Get retry decorator with exponential backoff

        Returns:
            Retry decorator
        """
        return retry(
            stop=stop_after_attempt(self.settings.max_retries),
            wait=wait_exponential(
                multiplier=self.settings.retry_backoff_multiplier,
                min=2,
                max=10
            ),
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
            reraise=True
        )

    async def __call__(self, **kwargs) -> Any:
        """
        Make the tool callable

        Args:
            **kwargs: Tool parameters

        Returns:
            Any: Tool result
        """
        logger.info(f"Executing tool: {self.name}", parameters=kwargs)
        try:
            result = await self.execute(**kwargs)
            logger.info(f"Tool {self.name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool {self.name} failed", error=str(e), exc_info=True)
            raise
