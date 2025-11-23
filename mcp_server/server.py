from mcp.server.fastmcp import FastMCP
import logging
from datetime import datetime
import json
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GroceryMCPServer")

# Create MCP server instance
mcp = FastMCP("Grocery Stock Server", port=8001, host="0.0.0.0")


def load_stock_db():
    try:
        stock_file = Path(__file__).parent.parent / "data" / "stock.json" 
        with open(stock_file, 'r') as f:
            stock_list = json.load(f)
        
        # Convert list to dict with product_id as key
        stock_db = {item["product_id"]: item for item in stock_list}
        logger.info(f"Loaded {len(stock_db)} products from {stock_file}")
        return stock_db
    
    except Exception as e:
        logger.error(f"Error loading stock.json: {e}")
        return {}
# Load stock database
STOCK_DB = load_stock_db()

@mcp.tool()
async def get_stock_price(product_id: str) -> dict:
    """
        Get stock price and availability for a product.
    """
    try:
        logger.info(f"Tool called: get_stock_price of product=${product_id}")

        if product_id in STOCK_DB:
            stock_info = STOCK_DB[product_id]
            
            
            logger.info(f"Stock check for {product_id}: {stock_info['quantity']} units available")
            
            return {
                "success": True,
                "product_id": product_id,
                "name": stock_info["name"],
                "price": stock_info.get("price", 0.0),
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
        logger.info("Starting Grocery Stock MCP Server on port 0.0.0.0:8001...")
        logger.info(f"Loaded {len(STOCK_DB)} products in stock database")
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")


if __name__ == "__main__":
    main()
    