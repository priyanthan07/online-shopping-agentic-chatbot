from langchain.tools import tool
from langchain_openai import ChatOpenAI
from typing import Dict, Optional, List
from pydantic import BaseModel, Field
import json
from pathlib import Path
from src.config import DATA_DIR, OPENAI_API_KEY, MODEL_NAME
from src.monitoring.logger import setup_logger

logger = setup_logger(__name__)

class NormalizedItem(BaseModel):
    original_text: str
    normalized_name: str
    quantity: int
    reasoning: str
    
class ItemNormalizationList(BaseModel):
    items: List[NormalizedItem]

# Load orders from JSON file
def load_orders_db() -> Dict:
    """Load orders database from JSON file"""
    try:
        orders_file = DATA_DIR / "orders.json"
        with open(orders_file, 'r') as f:
            orders_list = json.load(f)
        
        # Convert list to dict with order_id as key
        orders_db = {order["order_id"]: order for order in orders_list}
        logger.info(f"Loaded {len(orders_db)} orders from {orders_file}")
        return orders_db
    
    except FileNotFoundError:
        logger.warning("orders.json not found, using empty database")
        return {}
    
    except Exception as e:
        logger.error(f"Error loading orders.json: {e}")
        return {}

# Load orders database
ORDERS_DB = load_orders_db()

normalization_llm = ChatOpenAI(model=MODEL_NAME, temperature=0, api_key=OPENAI_API_KEY)
structured_llm = normalization_llm.with_structured_output(ItemNormalizationList)
    
@tool
def create_refund(order_id: str, reason: str = "Customer request") -> str:
    """
        Create a refund for an order.
    """
    logger.info(f"Tool called: create_refund for order '{order_id}'")
    try:
        if order_id not in ORDERS_DB:
            logger.warning(f"Order {order_id} not found")
            return json.dumps({
                "success": False,
                "error": f"Order {order_id} not found in system."
            })
        
        order = ORDERS_DB[order_id]
        amount = order['total']
        
        logger.info(f"Creating refund for {order_id}: ${amount}")
        
        # Return refund information
        return json.dumps({
            "success": True,
            "refund_id": f"REF{order_id}",
            "order_id": order_id,
            "amount": amount,
            "reason": reason,
            "status": "pending",
            "message": f"Refund of ${amount} initiated for order {order_id}. You will receive it in 5-7 business days."
        })
        
    except Exception as e:
        logger.error(f"Error creating refund for {order_id}: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": f"Error processing refund: {str(e)}"
        })
        
def normalize_items_with_llm(items_str: str, products) -> List[NormalizedItem]:
    """
        Use LLM to normalize item names and extract quantities
    """
    try:
        
        product_names = [p['name'] for p in products]
        
        prompt = f"""You are a product name normalizer for a grocery store.

                    Available products in our store:
                    {', '.join(product_names)}

                    User's shopping list: "{items_str}"

                    For each item in the user's list:
                    1. Identify the most likely matching product from our available products
                    2. Extract any quantity mentioned (e.g., "two eggs"-> quantity: 2, "eggs"-> quantity: 1)
                    3. Normalize the item name to match our product catalog
                    4. Provide reasoning

                    Examples:
                    - "two eggs"-> normalized_name: "eggs", quantity: 2
                    - "chicken"-> normalized_name: "chicken", quantity: 1
                    - "a dozen eggs"-> normalized_name: "eggs", quantity: 1 (we sell by dozen)
                    - "milk"-> normalized_name: "milk", quantity: 1
                    - "3 apples"-> normalized_name: "apples", quantity: 3

                    Parse the items and provide normalized versions.
                """
        
        result = structured_llm.invoke(prompt)
        logger.info(f"LLM normalized {len(result.items)} items")
        
        for item in result.items:
            logger.info(
                f"  '{item.original_text}'-> '{item.normalized_name}' "
                f"(qty: {item.quantity}) -> {item.reasoning}"
            )
        
        return result.items
        
    except Exception as e:
        logger.error(f"Error in LLM normalization: {e}", exc_info=True)
        # Fallback: simple split
        items_list = [item.strip() for item in items_str.split(',')]
        return [
            NormalizedItem(
                original_text=item,
                normalized_name=item,
                quantity=1,
                reasoning="Fallback normalization"
            ) for item in items_list
        ]
        
@tool
def calculate_budget(items: str, budget: float) -> str:
    """
        Calculate if items fit within budget with intelligent item matching.
    """
    logger.info(f"Tool called: calculate_budget with budget=${budget}")

    try:
        # Load products from products.json
        with open(DATA_DIR / "products.json", 'r') as f:
            products = json.load(f)
        
        # Use LLM to normalize items
        normalized_items = normalize_items_with_llm(items, products)
        
        total_cost = 0
        found_items = []
        not_found = []
        
        # Process each normalized item
        for norm_item in normalized_items:
            item_name = norm_item.normalized_name.lower()
            quantity = norm_item.quantity
            found = False
            
            logger.info(f"Processing: '{norm_item.original_text}'-> '{item_name}' (qty: {quantity})")
            
            # Try to match with products
            for product in products:
                product_name_lower = product['name'].lower()
                
                # Check if normalized name appears in product name
                if item_name in product_name_lower or product_name_lower in item_name:
                    if product['in_stock']:
                        item_cost = product['price'] * quantity
                        total_cost += item_cost
                        found_items.append({
                            "original": norm_item.original_text,
                            "matched": product['name'],
                            "price": product['price'],
                            "quantity": quantity,
                            "total": item_cost
                        })
                        logger.info(
                            f" Matched '{norm_item.original_text}'-> {product['name']} "
                            f"{quantity} = ${item_cost:.2f}"
                        )
                        found = True
                    else:
                        logger.info(f"  {product['name']} is out of stock")
                        not_found.append(f"{product['name']} (out of stock)")
                        found = True
                    break
            
            if not found:
                not_found.append(norm_item.original_text)
                logger.info(f"   No match found for '{norm_item.original_text}'")
        
        # Calculate results
        within_budget = total_cost <= budget
        remaining = budget - total_cost
        
        logger.info(
            f"Budget calculation: ${total_cost:.2f} vs ${budget:.2f} - "
            f"Within budget: {within_budget}"
        )
        
        # Build detailed response
        response_parts = []
        
        # Found items breakdown
        if found_items:
            response_parts.append(" Items found:")
            for item in found_items:
                if item['quantity'] > 1:
                    response_parts.append(
                        f"  • {item['original']}-> {item['matched']} "
                        f"x{item['quantity']} = ${item['total']:.2f} "
                        f"(${item['price']:.2f} each)"
                    )
                else:
                    response_parts.append(
                        f"  • {item['original']}-> {item['matched']}: ${item['price']:.2f}"
                    )
        
        # Not found items
        if not_found:
            response_parts.append("")
            response_parts.append(" Not available:")
            for item in not_found:
                response_parts.append(f"  • {item}")
        
        # Budget summary
        response_parts.append("")
        response_parts.append("=" * 40)
        if within_budget:
            response_parts.append(
                f"Total: ${total_cost:.2f} -  Within your ${budget:.2f} budget!"
            )
            response_parts.append(f"Remaining: ${remaining:.2f}")
        else:
            overage = abs(remaining)
            response_parts.append(
                f"Total: ${total_cost:.2f} - Exceeds your ${budget:.2f} budget by ${overage:.2f}"
            )
        
        return "\n".join(response_parts)
        
    except Exception as e:
        logger.error(f"Error calculating budget: {e}", exc_info=True)
        return f"Error calculating budget: {str(e)}"

    
# All tools
grocery_tools = [
    create_refund,
    calculate_budget
]