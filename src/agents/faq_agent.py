from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_openai_functions_agent
from src.rag.retriever import RAGRetriever
from src.config import MODEL_NAME, OPENAI_API_KEY
from langfuse.langchain import CallbackHandler

class FAQAgent:
    def __init__(self, langfuse_handler: CallbackHandler):
        self.llm = ChatOpenAI(model=MODEL_NAME, temperature=0,api_key=OPENAI_API_KEY)
        self.retriever = RAGRetriever()
        self.langfuse_handler = langfuse_handler
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful FAQ assistant for an online grocery store.
            
                        Use the following context to answer questions accurately:

                        {context}

                        Guidelines:
                        - Answer based on the provided context
                        - If the answer isn't in the context, say you don't know
                        - Be concise and helpful
                        - Focus on FAQs, policies, and general information
                        - Don't make assumptions about specific orders or products not in context"""),
                                    ("human", "{input}"),
                                    ("placeholder", "{agent_scratchpad}")
                        ])
        
    def answer(self, question: str) -> str:
        """
            Answer FAQ questions using RAG
        """

        context = self.retriever.get_context(question)
        
        # Create agent
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=[],
            prompt=self.prompt
        )
        
        agent_executor = AgentExecutor(
            agent=agent,
            tools=[],
            verbose=True,
            handle_parsing_errors=True
        )
        
        # Execute with Langfuse tracing
        result = agent_executor.invoke(
            {
                "input": question,
                "context": context
            },
            config={"callbacks": [self.langfuse_handler]}
        )
        
        return result['output']