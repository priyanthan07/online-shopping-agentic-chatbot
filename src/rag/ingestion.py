import json
from pathlib import Path
from typing import List, Dict
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from src.config import DATA_DIR, CHROMA_PERSIST_DIR, EMBEDDING_MODEL

class DataIngestion:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
    def load_json_data(self, filename: str) -> List[Dict]:
        file_path = DATA_DIR / filename
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def create_documents(self) -> List[Document]:
        """
            Create documents from all data sources
        """
        documents = []
        
        # Load FAQs
        faqs = self.load_json_data("faqs.json")
        for faq in faqs:
            doc = Document(
                page_content=f"Question: {faq['question']}\nAnswer: {faq['answer']}",
                metadata={"type": "faq", "category": faq.get("category", "general")}
            )
            documents.append(doc)
        
        # Load Products
        products = self.load_json_data("products.json")
        for product in products:
            content = f"Product: {product['name']}\n"
            content += f"Category: {product['category']}\n"
            content += f"Price: ${product['price']}\n"
            content += f"Description: {product['description']}\n"
            content += f"In Stock: {product['in_stock']}"
            
            doc = Document(
                page_content=content,
                metadata={
                    "type": "product",
                    "product_id": product['id'],
                    "category": product['category'],
                    "price": product['price']
                }
            )
            documents.append(doc)
        
        # Load Policies
        policies = self.load_json_data("policies.json")
        for policy in policies:
            doc = Document(
                page_content=f"Policy: {policy['title']}\n{policy['content']}",
                metadata={"type": "policy", "policy_type": policy['type']}
            )
            documents.append(doc)
        
        return documents

    def ingest_data(self):
        """
            Ingest all data into vector store
        """
        documents = self.create_documents()
        split_docs = self.text_splitter.split_documents(documents)
        
        vectorstore = Chroma.from_documents(
            documents=split_docs,
            embedding=self.embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )
        
        print(f"Ingested {len(split_docs)} document chunks into vector store")
        return vectorstore
    
def initialize_vectorstore():
    """
        Initialize or load vector store
    """
    ingestion = DataIngestion()
    return ingestion.ingest_data()