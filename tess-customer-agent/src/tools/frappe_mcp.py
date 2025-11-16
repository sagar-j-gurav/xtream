"""
Frappe MCP Client Wrapper for TESS
Integrates with Frappe CRM via Model Context Protocol (MCP)
"""
from typing import List, Dict, Any, Optional
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.tools import BaseTool

from src.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class FrappeMCPClient:
    """
    Client for Frappe MCP integration

    Automatically discovers and loads tools from the Frappe MCP server
    """

    def __init__(self):
        """Initialize Frappe MCP client"""
        self.settings = get_settings()
        self.client: Optional[MultiServerMCPClient] = None
        self.tools: List[BaseTool] = []
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize MCP client and load tools

        This method connects to the Frappe MCP server and
        auto-discovers all available tools
        """
        if self._initialized:
            logger.debug("Frappe MCP client already initialized")
            return

        logger.info("Initializing Frappe MCP client")

        # Build MCP server configuration
        mcp_config = {
            "frappe": {
                "transport": "streamable_http",
                "url": self.settings.frappe_mcp_url,
                "timeout": self.settings.mcp_timeout,
            }
        }

        # Add authentication headers if API key and secret are provided
        if self.settings.frappe_api_key and self.settings.frappe_api_secret:
            mcp_config["frappe"]["headers"] = {
                "Authorization": (
                    f"token {self.settings.frappe_api_key}:"
                    f"{self.settings.frappe_api_secret}"
                ),
                "Content-Type": "application/json"
            }
            logger.debug("Added authentication headers to MCP config")

        try:
            # Initialize MultiServerMCPClient
            self.client = MultiServerMCPClient(mcp_config)

            # Auto-discover and load tools from MCP server
            self.tools = await self.client.get_tools()

            logger.info(
                f"Successfully initialized Frappe MCP client with {len(self.tools)} tools",
                tools=[tool.name for tool in self.tools]
            )

            self._initialized = True

        except Exception as e:
            logger.error(
                "Failed to initialize Frappe MCP client",
                error=str(e),
                url=self.settings.frappe_mcp_url,
                exc_info=True
            )
            raise

    async def get_tools(self) -> List[BaseTool]:
        """
        Get all available MCP tools

        Returns:
            List[BaseTool]: List of LangChain-compatible tools
        """
        if not self._initialized:
            await self.initialize()

        return self.tools

    async def close(self) -> None:
        """Close MCP client connections"""
        if self.client:
            logger.info("Closing Frappe MCP client")
            # Note: MultiServerMCPClient may not have an explicit close method
            # depending on the implementation. Cleanup is usually automatic.
            self.client = None
            self._initialized = False

    def get_tool_by_name(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a specific tool by name

        Args:
            tool_name: Name of the tool

        Returns:
            Optional[BaseTool]: Tool if found, None otherwise
        """
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None

    def list_tool_names(self) -> List[str]:
        """
        Get list of all available tool names

        Returns:
            List[str]: List of tool names
        """
        return [tool.name for tool in self.tools]

    def get_tool_descriptions(self) -> Dict[str, str]:
        """
        Get descriptions of all available tools

        Returns:
            Dict[str, str]: Dictionary mapping tool names to descriptions
        """
        return {tool.name: tool.description for tool in self.tools}


# Singleton instance
_frappe_mcp_client: Optional[FrappeMCPClient] = None


async def get_frappe_mcp_client() -> FrappeMCPClient:
    """
    Get singleton instance of Frappe MCP client

    Returns:
        FrappeMCPClient: Frappe MCP client instance
    """
    global _frappe_mcp_client
    if _frappe_mcp_client is None:
        _frappe_mcp_client = FrappeMCPClient()
        await _frappe_mcp_client.initialize()
    return _frappe_mcp_client


async def get_all_mcp_tools() -> List[BaseTool]:
    """
    Get all MCP tools for use in LangGraph agent

    This function auto-discovers all tools from the Frappe MCP server
    without hardcoding any tool names or signatures.

    Returns:
        List[BaseTool]: List of all available MCP tools
    """
    client = await get_frappe_mcp_client()
    tools = await client.get_tools()

    logger.info(
        f"Retrieved {len(tools)} MCP tools for agent",
        tool_names=[t.name for t in tools]
    )

    return tools
