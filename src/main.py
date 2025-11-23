#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.orchestrator import OrchestratorAgent
from src.rag.ingestion import initialize_vectorstore
from src.monitoring.evaluator import AutoEvaluator
from src.monitoring.logger import setup_logger
from src.config import LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

# Setup logger
logger = setup_logger(__name__)


async def initialize_mcp():
    """Initialize MCP client connection"""
    from src.tools.mcp_tool import create_mcp_client
    try:
        logger.info("Initializing MCP Client...")
        client = create_mcp_client()
        await client._initialize_client()
        logger.info(" MCP client connected")
    except Exception as e:
        logger.warning(f"MCP initialization warning: {e}")


def initialize_system():
    """Initialize the chatbot system - REUSABLE by both CLI and Streamlit"""

    logger.info("Initializing Grocery Shopping Chatbot")
    
    # Initialize vector store
    logger.info("[1/4] Initializing Vector Store...")
    try:
        initialize_vectorstore()
        logger.info(" Vector store initialized")
    except Exception as e:
        logger.error(f"Error initializing vector store: {e}")
        logger.info("Continuing with existing vector store...")
    
    # Initialize Langfuse
    logger.info("[2/4] Connecting to Langfuse...")
    langfuse_handler = None
    try:
        langfuse = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_BASE_URL
        )
        
        langfuse_handler = CallbackHandler()
        langfuse_handler.langfuse = langfuse
        
        logger.info(" Langfuse connected")
        
    except Exception as e:
        logger.warning(f"Langfuse connection warning: {e}")
        logger.info("Continuing without Langfuse tracing...")
        langfuse_handler = None
    
    # Initialize MCP
    logger.info("[3/4] Connecting to MCP Server...")
    try:
        asyncio.run(initialize_mcp())
    except Exception as e:
        logger.warning(f"MCP warning: {e}")
    
    # Initialize Orchestrator
    logger.info("[4/4] Initializing Agent Orchestrator...")
    orchestrator = OrchestratorAgent(langfuse_handler)
    logger.info(" Orchestrator ready")
    
    logger.info("="*50)
    logger.info("System Ready!")
    logger.info("="*50)
    
    return orchestrator

def process_user_query(orchestrator, user_input: str, session_id: str):
    """
        Process user query - REUSABLE by both CLI and Streamlit
    """
    logger.info(f"Processing query for session: {session_id}")
    logger.info(f"User query: {user_input}")
    
    try:
        result = orchestrator.process(user_input, session_id)
        logger.info(f"Agent: {result['agent']}, Blocked: {result.get('blocked', False)}")
        return result
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        return {
            "response": f"I apologize, but I encountered an error processing your request: {str(e)}",
            "agent": "error",
            "blocked": False,
            "error": str(e)
        }


def run_evaluation(orchestrator):
    """
        Run evaluation suite - REUSABLE by both CLI and Streamlit
    """
    logger.info("Running evaluation suite")
    evaluator = AutoEvaluator()
    summary = evaluator.run_evaluation(orchestrator)
    logger.info(f"Evaluation complete: Pass rate {summary['pass_rate']:.2%}")
    return summary
