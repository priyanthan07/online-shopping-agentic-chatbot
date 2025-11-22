from mcp.server.fastmcp import FastMCP
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GroceryMCPServer")

# Create MCP server instance
mcp = FastMCP("Grocery Stock Server", port=8001)

# Mock stock database
STOCK_DB = {
    "P001": {"name": "Organic Milk", "quantity": 45, "warehouse": "Warehouse A"},
    "P002": {"name": "Whole Wheat Bread", "quantity": 30, "warehouse": "Warehouse B"},
    "P003": {"name": "Free Range Eggs", "quantity": 60, "warehouse": "Warehouse A"},
    "P004": {"name": "Bananas", "quantity": 120, "warehouse": "Warehouse C"},
    "P005": {"name": "Chicken Breast", "quantity": 25, "warehouse": "Warehouse B"},
    "P006": {"name": "Apples", "quantity": 80, "warehouse": "Warehouse C"},
    "P007": {"name": "Pasta", "quantity": 0, "warehouse": "Warehouse A"},
    "P008": {"name": "Rice", "quantity": 55, "warehouse": "Warehouse B"},
}

@mcp.tool()
async def get_stock_price(product_id: str) -> dict:
    """
        Get stock price and availability for a product.
    """
    try:
        if product_id in STOCK_DB:
            stock_info = STOCK_DB[product_id]
            
            # Mock pricing based on product
            prices = {
                "P001": 4.99, "P002": 3.49, "P003": 5.99, "P004": 0.59,
                "P005": 8.99, "P006": 1.99, "P007": 2.49, "P008": 12.99
            }
            
            logger.info(f"Stock check for {product_id}: {stock_info['quantity']} units available")
            
            return {
                "success": True,
                "product_id": product_id,
                "name": stock_info["name"],
                "price": prices.get(product_id, 0.0),
                "quantity": stock_info["quantity"],
                "warehouse": stock_info["warehouse"],
                "in_stock": stock_info["quantity"] > 0,
                "last_updated": datetime.now().isoformat()
            }
        else:
            logger.warning(f"Product {product_id} not found in inventory")
            return {
                "success": False,
                "error": f"Product {product_id} not found in inventory"
            }
    except Exception as e:
        logger.error(f"Error in get_stock_price: {e}")
        return {"success": False, "error": str(e)}


def main():
    """Start the MCP server"""
    try:
        logger.info("Starting Grocery Stock MCP Server on port 8001...")
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")


if __name__ == "__main__":
    main()
    