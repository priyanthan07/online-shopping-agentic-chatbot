from langchain.tools import tool
from typing import Dict, Optional
import json
from pathlib import Path
from src.config import DATA_DIR

# Mock database
ORDERS_DB = {
    "ORD001": {"total": 45.99, "status": "delivered", "items": ["milk", "bread"]},
    "ORD002": {"total": 89.50, "status": "shipped", "items": ["apples", "chicken"]},
    "ORD003": {"total": 120.00, "status": "processing", "items": ["rice", "pasta"]}
}

CART = {}

@tool
def get_item_price(item_name: str) -> str:
    """Get the current price of a grocery item by name.
    """
    try:
        with open(DATA_DIR/"products.json", 'r' ) as f:
            products = json.load(f)
            
        item_name_lower = item_name.lower()
        for product in products:
            if item_name_lower is product['name'].lower():
                if product['in_stock']:
                    return f"{product['name']} costs ${product['price']}. It is currently in stock."
                else:
                    return f"{product['name']} costs ${product['price']} but is currently out of stock."
        return f"Item '{item_name}' not found in our inventory."
    
    except Exception as e:
        return f"Error retrieving price: {str(e)}"
    
@tool
def create_refund(order_id: str, reason: str = "Customer request") -> str:
    """
        Create a refund for an order.
    """
    try:
        if order_id not in ORDERS_DB:
            return f"Error: Order {order_id} not found."
        
        order = ORDERS_DB[order_id]
        amount = order['total']
        
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
        return f"Error in create refund: {str(e)}"
        
@tool
def calculate_budget(items: str, budget: float) -> str:
    """
        Calculate if items fit within budget and suggest alternatives if needed.
    """
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
                    break
        result = {
            "total_cost": round(total_cost, 2),
            "budget": budget,
            "within_budget": total_cost <= budget,
            "items": found_items,
            "remaining": round(budget - total_cost, 2)
        }
        
        if total_cost <= budget:
            return f"Great! Your items total ${result['total_cost']}, which is within your ${budget} budget. You have ${result['remaining']} remaining."
        else:
            return f"Your selected items total ${result['total_cost']}, which exceeds your ${budget} budget by ${round(total_cost - budget, 2)}. Consider removing some items."
        
    except Exception as e:
        return f"Error calculating budget: {str(e)}"

@tool
def add_to_cart(item_name: str, quantity: int = 1) -> str:
    """
        Add an item to the shopping cart.
    """
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
                else:
                    CART[product['id']] = {
                        'name': product['name'],
                        'price': product['price'],
                        'quantity': quantity
                    }
                
                total_items = sum(item['quantity'] for item in CART.values())
                return f"Added {quantity} x {product['name']} to cart. Cart now has {total_items} items."
        
        return f"Item '{item_name}' not found."
        
    except Exception as e:
        return f"Error adding to cart: {str(e)}"

@tool
def get_cart_summary() -> str:
    """
        Get a summary of items currently in
    """
    if not CART:
        return "Your cart is empty."
    
    summary = "Your Cart:\n"
    total = 0
    
    for item_id, item_data in CART.items():
        item_total = item_data['price'] * item_data['quantity']
        total += item_total
        summary += f"- {item_data['name']}: {item_data['quantity']} x ${item_data['price']} = ${item_total}\n"
    
    summary += f"\nTotal: ${round(total, 2)}"
    return summary
    
# All tools
grocery_tools = [
    get_item_price,
    create_refund,
    calculate_budget,
    add_to_cart,
    get_cart_summary
]