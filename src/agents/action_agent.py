from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_openai_functions_agent
from src.tools.grocery_tools import grocery_tools
from src.tools.mcp_tool import mcp_tools
from src.rag.retriever import RAGRetriever
from src.config import MODEL_NAME, OPENAI_API_KEY
from langfuse.langchain import CallbackHandler

class ActionAgent:
    def __init__(self, langfuse_handler: CallbackHandler):
        self.llm = ChatOpenAI(model=MODEL_NAME, temperature=0, api_key=OPENAI_API_KEY)
        self.retriever = RAGRetriever()
        self.langfuse_handler = langfuse_handler
        self.tools = grocery_tools + mcp_tools
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an action-oriented assistant for an online grocery store.

                        You have access to the following tools to help customers:
                        - get_item_price: Check prices of items
                        - add_to_cart: Add items to shopping cart
                        - get_cart_summary: View cart contents
                        - calculate_budget: Check if items fit within budget
                        - create_refund: Process refunds for orders
                        - get_stock_availability: Check real-time stock via MCP

                        Product Context:
                        {context}

                        Guidelines:
                        - Use tools to perform actions (checking prices, adding to cart, refunds, etc.)
                        - Be proactive in suggesting actions
                        - Confirm actions with users before executing critical operations
                        - Provide clear feedback on tool results
                        - For product information, use the context provided"""),
                                    ("human", "{input}"),
                                    ("placeholder", "{agent_scratchpad}")
                    ])
    
    def execute(self, task: str) -> str:
        """Execute actions using tools"""
        # Get product context if needed
        context = self.retriever.get_context(task, filter_type="product")
        
        # Create agent
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )
        
        # Execute with Langfuse tracing
        result = agent_executor.invoke(
            {
                "input": task,
                "context": context
            },
            config={"callbacks": [self.langfuse_handler]}
        )
        
        return result['output']