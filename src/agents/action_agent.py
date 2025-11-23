from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from src.tools.grocery_tools import grocery_tools
from src.tools.mcp_tool import mcp_tools
from src.rag.retriever import RAGRetriever
from src.guardrails.safety import SafetyGuardrails
from src.config import MODEL_NAME, OPENAI_API_KEY
from src.monitoring.logger import setup_logger
from langfuse.langchain import CallbackHandler
from typing import Optional, Literal
from pydantic import BaseModel, Field
import re

class RefundIntentDetection(BaseModel):
    has_refund_intent: bool
    order_id: Optional[str]
    reasoning: str

class ActionAgent:
    def __init__(self, langfuse_handler: Optional[CallbackHandler], guardrails:SafetyGuardrails):
        self.llm = ChatOpenAI(model=MODEL_NAME, temperature=0, api_key=OPENAI_API_KEY)
        self.retriever = RAGRetriever()
        self.langfuse_handler = langfuse_handler
        self.tools = grocery_tools + mcp_tools
        self.logger = setup_logger(__name__)
        self.guardrails = guardrails
        
        self.structured_intent_llm = self.llm.with_structured_output(RefundIntentDetection)
        
        self.prompt = """You are an action-oriented assistant for an online grocery store.

                        You have access to tools to help customers:
                        - calculate_budget: Check if items fit within budget
                        - create_refund: Process refunds for orders
                        - get_stock_price: Check real-time stock via MCP

                        Guidelines:
                        - Use tools to perform actions
                        - Be proactive in suggesting actions
                        - Provide clear feedback on tool results
                    """
        
        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.prompt
        )
        
        self.logger.info(f"Available tools: {[tool.name for tool in self.tools]}")
    
    def _check_refund_intent(self, task: str) -> Optional[str]:
        """
            Use LLM to check if task is a refund request and extract order ID
        """
        self.logger.info(f"Checking refund intent for: {task[:50]}...")
        
        try:
            # Prompt for structured refund intent detection
            intent_prompt = f"""Analyze this user message and determine if it's a refund request for an order.

                    A refund request typically includes:
                    - Words like: "refund", "return money", "get my money back", "cancel order", "want my money back", "process refund"
                    - An order ID in format: ORD followed by 3-4 digits (e.g., ORD001, ORD1234)

                    User message: "{task}"

                    Determine:
                    1. Is this a refund request? (true/false)
                    2. Extract order ID if present (format: ORD###, e.g., ORD001)
                    3. Brief reasoning

                    Examples:
                    - "I want a refund for order ORD001" → has_refund_intent: true, order_id: "ORD001"
                    - "Create a refund for ORD999" → has_refund_intent: true, order_id: "ORD999"
                    - "What's the status of my order ORD001?" → has_refund_intent: false, order_id: None
                    - "How do I return an item?" → has_refund_intent: false, order_id: None
                """
            
            # Get structured output from LLM
            result = self.structured_intent_llm.invoke(intent_prompt)
            
            self.logger.info(
                f"Refund intent detection: has_intent={result.has_refund_intent}, "
                f"order_id={result.order_id} "
                f"reason={result.reasoning}"
            )
            
            # Only return order_id if refund intent detected
            if result.has_refund_intent and result.order_id:
                self.logger.info(f"Refund intent detected for order: {result.order_id}")
                return result.order_id
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error in refund intent detection: {e}", exc_info=True)
            return None
    
    def execute(self, task: str) -> str:
        """Execute actions using tools"""

        self.logger.info(f"ActionAgent executing task")
        self.logger.info(f"Task: {task[:100]}...")
        
        try:
            order_id = self._check_refund_intent(task)
            
            if order_id:
                self.logger.info(f"Refund intent detected for order: {order_id}")
                
                # Validate refund BEFORE calling tool
                is_valid, error_msg = self.guardrails.validate_refund_request(order_id)
                
                if not is_valid:
                    self.logger.warning(f"Refund blocked by guardrails: {error_msg}")
                    return error_msg
                
                self.logger.info(f"Refund validation passed for {order_id}")
                
            # Get product context if needed
            context = self.retriever.get_context(task, filter_type="product")
            self.logger.info(f"Retrieved context length: {len(context)} chars")
            
            full_task = f"Product Context: {context}\n\nTask: {task}"
            
            # Create agent
            result = self.agent.invoke(
                {"messages": [{"role": "user", "content": full_task}]},
                config={"callbacks": [self.langfuse_handler]}
            )
            
            response = result["messages"][-1].content
            
            self.logger.info("ActionAgent task completed successfully")
            self.logger.info(f"Response: {response[:100]}...")
            
            return response
        
        except Exception as e:
            self.logger.error(f"ActionAgent error: {e}", exc_info=True)
            raise
        