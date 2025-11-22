from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from src.tools.grocery_tools import grocery_tools
from src.tools.mcp_tool import mcp_tools
from src.rag.retriever import RAGRetriever
from src.config import MODEL_NAME, OPENAI_API_KEY
from src.monitoring.logger import setup_logger
from langfuse.langchain import CallbackHandler

class ActionAgent:
    def __init__(self, langfuse_handler: CallbackHandler):
        self.llm = ChatOpenAI(model=MODEL_NAME, temperature=0, api_key=OPENAI_API_KEY)
        self.retriever = RAGRetriever()
        self.langfuse_handler = langfuse_handler
        self.tools = grocery_tools + mcp_tools
        self.logger = setup_logger(__name__)
        
        self.prompt = """You are an action-oriented assistant for an online grocery store.

                        You have access to tools to help customers:
                        - get_item_price: Check prices of items
                        - add_to_cart: Add items to shopping cart
                        - get_cart_summary: View cart contents
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
        
        self.logger.info("ActionAgent initialized with tools")
        self.logger.debug(f"Available tools: {[tool.name for tool in self.tools]}")
    
    def execute(self, task: str) -> str:
        """Execute actions using tools"""

        self.logger.info(f"ActionAgent executing task")
        self.logger.debug(f"Task: {task[:100]}...")
        try:
            # Get product context if needed
            context = self.retriever.get_context(task, filter_type="product")
            self.logger.debug(f"Retrieved context length: {len(context)} chars")
            
            full_task = f"Product Context: {context}\n\nTask: {task}"
            
            # Create agent
            result = self.agent.invoke(
                {"messages": [{"role": "user", "content": full_task}]},
                config={"callbacks": [self.langfuse_handler]}
            )
            
            response = result["messages"][-1].content
            
            self.logger.info("ActionAgent task completed successfully")
            self.logger.debug(f"Response: {response[:100]}...")
            
            return response
        
        except Exception as e:
            self.logger.error(f"ActionAgent error: {e}", exc_info=True)
            raise
        