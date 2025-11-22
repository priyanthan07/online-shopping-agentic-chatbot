import asyncio
import json
import logging
from typing import Dict, Any, List
from langchain.tools import tool
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from src.config import MCP_SERVER_URL

logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self):
        self.server_url = MCP_SERVER_URL
        self.available_tools: List[Dict[str, Any]] = []
        self.tools_discovered = False
    
    async def _initialize_client(self):
        """Initialize connection and discover available tools"""
        if self.tools_discovered:
            return
        
        try:
            logger.info(f"Initialize MCP Client and URL: {self.server_url}")
            
            # Discover tools
            async with streamablehttp_client(self.server_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    response = await session.list_tools()
                    tools = response.tools
                    
                    self.available_tools = [{
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                    } for tool in tools]
                    
                    self.tools_discovered = True
                    logger.info(f"Discovered tools: {[tool.name for tool in tools]}")
                    
        except Exception as e:
            logger.error(f"Failed to discover tools: {e}")
            raise
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        try:
            async with streamablehttp_client(self.server_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=parameters)
                    
                    if hasattr(result, 'content') and result.content:
                        content_text = result.content[0].text if result.content else ""
                        try:
                            parsed_content = json.loads(content_text)
                            return parsed_content
                        except json.JSONDecodeError:
                            return {"success": True, "result": content_text}
                    else:
                        return {"success": True, "result": str(result)}
        
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return {"success": False, "error": str(e)}


# Global MCP client instance
_mcp_client = None


def create_mcp_client() -> MCPClient:
    """Create MCP client"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


@tool
def get_stock_price(product_id: str) -> str:
    """Get stock price and availability via MCP server (implements MCP requirement).
    
    Args:
        product_id: Product ID to check stock and price for
        
    Returns:
        Stock price and availability information
    """
    try:
        client = create_mcp_client()
        
        result = asyncio.run(client.call_tool(
            "get_stock_price",
            {"product_id": product_id}
        ))
        
        if result.get("success"):
            in_stock = "in stock" if result.get('in_stock') else "out of stock"
            return f"{result['name']}: ${result['price']} - {result['quantity']} units available ({in_stock}) at {result['warehouse']}"
        else:
            return f"Error: {result.get('error', 'Unknown error')}"
            
    except Exception as e:
        logger.error(f"MCP tool error: {e}")
        return f"MCP Error: {str(e)}"


# Export MCP tools - only get_stock_price as per task requirement
mcp_tools = [get_stock_price]