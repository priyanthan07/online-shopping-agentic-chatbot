from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from typing import List
from src.monitoring.logger import setup_logger
from src.config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL

class RAGRetriever:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        self.vectorstore = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=self.embeddings
        )
        self.retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": 5}
        )
        self.logger = setup_logger(__name__)
        self.logger.info("RAG Retriever initialized")
    
    def retrieve(self, query: str, filter_type: str = None) -> List[Document]:
        """
            Retrieve relevant documents
        """
        self.logger.debug(f"Retrieving documents for query: {query[:50]}...")
        if filter_type:
            self.logger.debug(f"Applying filter: type={filter_type}")
            retriever = self.vectorstore.as_retriever(
                search_kwargs={
                    "k": 5,
                    "filter": {"type": filter_type}
                }
            )
            docs = retriever.get_relevant_documents(query)
        else:
            docs = self.retriever.get_relevant_documents(query)
            
        self.logger.info(f"Retrieved {len(docs)} documents")
        
        return docs
    
    def get_context(self, query: str, filter_type: str = None) -> str:
        """
            Get formatted context for query
        """
        docs = self.retrieve(query, filter_type)
        context = "\n\n".join([doc.page_content for doc in docs])
        self.logger.debug(f"Context length: {len(context)} characters")
        return context