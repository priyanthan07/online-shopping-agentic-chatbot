from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from typing import List
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
    
    def retrieve(self, query: str, filter_type: str = None) -> List[Document]:
        """
            Retrieve relevant documents
        """
        if filter_type:
            retriever = self.vectorstore.as_retriever(
                search_kwargs={
                    "k": 5,
                    "filter": {"type": filter_type}
                }
            )
            return retriever.get_relevant_documents(query)
        return self.retriever.get_relevant_documents(query)
    
    def get_context(self, query: str, filter_type: str = None) -> str:
        """
            Get formatted context for query
        """
        docs = self.retrieve(query, filter_type)
        context = "\n\n".join([doc.page_content for doc in docs])
        return context