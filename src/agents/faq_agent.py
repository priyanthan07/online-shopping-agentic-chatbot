from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from src.rag.retriever import RAGRetriever
from src.config import MODEL_NAME, OPENAI_API_KEY
from src.monitoring.logger import setup_logger
from langfuse.langchain import CallbackHandler

class FAQAgent:
    def __init__(self, langfuse_handler: CallbackHandler):
        self.llm = ChatOpenAI(model=MODEL_NAME, temperature=0,api_key=OPENAI_API_KEY)
        self.retriever = RAGRetriever()
        self.langfuse_handler = langfuse_handler
        self.logger = setup_logger(__name__)
        self.prompt = """You are a helpful FAQ assistant for an online grocery store.

                        Guidelines:
                        - Answer based on the provided context
                        - If the answer isn't in the context, say you don't know
                        - Be concise and helpful
                        - Focus on FAQs, policies, and general information
                    """
        self.agent = create_agent(
            model=self.llm,
            tools=[],
            system_prompt=self.prompt
        )
        self.logger.info("FAQAgent initialized")
        
    def answer(self, question: str) -> str:
        """
            Answer FAQ questions using RAG
        """
        self.logger.info(f"FAQAgent answering question")
        self.logger.debug(f"Question: {question}")
        
        try:
            context = self.retriever.get_context(question)
            self.logger.debug(f"Retrieved context length: {len(context)} chars")
            
            full_question = f"Context: {context}\n\nQuestion: {question}"
            
            result = self.agent.invoke(
                {"messages": [{"role": "user", "content": full_question}]},
                config={"callbacks": [self.langfuse_handler]}
            )
            response = result["messages"][-1].content
            self.logger.info("FAQAgent answered successfully")
            self.logger.debug(f"Answer: {response[:100]}...")
            
            return response
        
        except Exception as e:
            self.logger.error(f"FAQAgent error: {e}", exc_info=True)
            raise
        