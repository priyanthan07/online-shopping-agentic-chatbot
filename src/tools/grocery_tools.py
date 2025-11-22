from langchain.tools import tool
from typing import Dict, Optional
import json
from pathlib import Path
from src.config import DATA_DIR
from src.monitoring.logger import setup_logger

logger = setup_logger(__name__)

# Mock database
ORDERS_DB = {
    "ORD001": {"total": 45.99, "status": "delivered", "items": ["milk", "bread"]},
    "ORD002": {"total": 89.50, "status": "shipped", "items": ["apples", "chicken"]},
    "ORD003": {"total": 120.00, "status": "processing", "items": ["rice", "pasta"]}
}

CART = {}

@tool
def get_item_price(item_name: str) -> str:
    """
        Get the current price of a grocery item by name.
    """
    logger.info(f"Tool called: get_item_price for '{item_name}'")
    
    try:
        with open(DATA_DIR/"products.json", 'r' ) as f:
            products = json.load(f)
            
        item_name_lower = item_name.lower()
        for product in products:
            if item_name_lower is product['name'].lower():
                if product['in_stock']:
                    logger.info(f"Price found: {product['name']} = ${product['price']} (in stock)")
                    return f"{product['name']} costs ${product['price']}. It is currently in stock."
                else:
                    logger.warning(f"Product {product['name']} is out of stock")
                    return f"{product['name']} costs ${product['price']} but is currently out of stock."
        logger.warning(f"Item '{item_name}' not found in inventory")
        return f"Item '{item_name}' not found in our inventory."
    
    except Exception as e:
        logger.error(f"Error retrieving price for '{item_name}': {e}", exc_info=True)
        return f"Error retrieving price: {str(e)}"
    
@tool
def create_refund(order_id: str, reason: str = "Customer request") -> str:
    """
        Create a refund for an order.
    """
    logger.info(f"Tool called: create_refund for order '{order_id}'")
    logger.debug(f"Refund reason: {reason}")
    
    try:
        if order_id not in ORDERS_DB:
            logger.warning(f"Order {order_id} not found")
            return f"Error: Order {order_id} not found."
        
        order = ORDERS_DB[order_id]
        amount = order['total']
        
        logger.info(f"Creating refund for {order_id}: ${amount}")
        
        refund_data = {
            "order_id": order_id,
            "amount": amount,
            "reason": reason,
            "status": "pending"
        }
        
        return json.dumps({
            "success": True,
            "refund_id": f"REF{order_id}",
            "amount": amount,
            "message": f"Refund of ${amount} initiated for order {order_id}. You will receive it in 5-7 business days."
        })
        
    except Exception as e:
        logger.error(f"Error creating refund for {order_id}: {e}", exc_info=True)
        return f"Error in create refund: {str(e)}"
        
@tool
def calculate_budget(items: str, budget: float) -> str:
    """
        Calculate if items fit within budget and suggest alternatives if needed.
    """
    logger.info(f"Tool called: calculate_budget with budget=${budget}")
    logger.debug(f"Items requested: {items}")

    try:
        with open(DATA_DIR / "products.json", 'r') as f:
            products = json.load(f)
            
        item_list = [item.strip().lower() for item in items.split(',')]
        total_cost = 0
        found_items = []
        
        for item_name in item_list:
            for product in products:
                if item_name in product['name'].lower():
                    if product['in_stock']:
                        total_cost += product['price']
                        found_items.append({
                            "name": product['name'],
                            "price": product['price']
                        })
                        logger.debug(f"Added {product['name']}: ${product['price']}")
                    break
        result = {
            "total_cost": round(total_cost, 2),
            "budget": budget,
            "within_budget": total_cost <= budget,
            "items": found_items,
            "remaining": round(budget - total_cost, 2)
        }
        
        logger.info(f"Budget calculation: ${result['total_cost']} vs ${budget} - Within budget: {result['within_budget']}")
        
        if total_cost <= budget:
            return f"Great! Your items total ${result['total_cost']}, which is within your ${budget} budget. You have ${result['remaining']} remaining."
        else:
            return f"Your selected items total ${result['total_cost']}, which exceeds your ${budget} budget by ${round(total_cost - budget, 2)}. Consider removing some items."
        
    except Exception as e:
        logger.error(f"Error calculating budget: {e}", exc_info=True)
        return f"Error calculating budget: {str(e)}"

@tool
def add_to_cart(item_name: str, quantity: int = 1) -> str:
    """
        Add an item to the shopping cart.
    """
    logger.info(f"Tool called: add_to_cart - '{item_name}' x{quantity}")
    
    try:
        with open(DATA_DIR / "products.json", 'r') as f:
            products = json.load(f)
            
        item_name_lower = item_name.lower()
        for product in products:
            if item_name_lower in product['name'].lower():
        
                if not product['in_stock']:
                    return f"Sorry, {product['name']} is currently out of stock."
                        
                if product['id'] in CART:
                    CART[product['id']]['quantity'] += quantity
                    logger.warning(f"Cannot add {product['name']} - out of stock")
                else:
                    CART[product['id']] = {
                        'name': product['name'],
                        'price': product['price'],
                        'quantity': quantity
                    }
                    logger.debug(f"Added new item {product['name']} to cart")
                
                total_items = sum(item['quantity'] for item in CART.values())
                logger.info(f"Cart updated: {total_items} total items")
                return f"Added {quantity} x {product['name']} to cart. Cart now has {total_items} items."
        
        logger.warning(f"Item '{item_name}' not found")
        return f"Item '{item_name}' not found."
        
    except Exception as e:
        logger.error(f"Error adding to cart: {e}", exc_info=True)
        return f"Error adding to cart: {str(e)}"

@tool
def get_cart_summary() -> str:
    """
        Get a summary of items currently in
    """
    logger.info("Tool called: get_cart_summary")
    
    if not CART:
        logger.debug("Cart is empty")
        return "Your cart is empty."
    
    summary = "Your Cart:\n"
    total = 0
    
    for item_id, item_data in CART.items():
        item_total = item_data['price'] * item_data['quantity']
        total += item_total
        summary += f"- {item_data['name']}: {item_data['quantity']} x ${item_data['price']} = ${item_total}\n"
    
    summary += f"\nTotal: ${round(total, 2)}"
    logger.info(f"Cart summary: {len(CART)} unique items, total ${round(total, 2)}")
    return summary
    
# All tools
grocery_tools = [
    get_item_price,
    create_refund,
    calculate_budget,
    add_to_cart,
    get_cart_summary
]