#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.orchestrator import OrchestratorAgent
from src.rag.ingestion import initialize_vectorstore
from src.monitoring.evaluator import AutoEvaluator
from langfuse import Langfuse
from langfuse.langchain  import CallbackHandler
from src.config import LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL
import argparse


def initialize_system():
    """Initialize the chatbot system"""
    print("Initializing Grocery Shopping Chatbot...")
    print("="*50)
    
    # Initialize vector store
    print("\n[1/3] Initializing Vector Store...")
    try:
        initialize_vectorstore()
        print("✓ Vector store initialized")
    except Exception as e:
        print(f"✗ Error initializing vector store: {e}")
        print("  Continuing with existing vector store...")
    
    # Initialize Langfuse
    print("\n[2/3] Connecting to Langfuse...")
    try:
        langfuse = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_BASE_URL
        )
        langfuse_handler = CallbackHandler(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_BASE_URL
        )
        print("✓ Langfuse connected")
    except Exception as e:
        print(f"⚠ Langfuse connection warning: {e}")
        print("  Continuing without Langfuse tracing...")
        langfuse_handler = None
    
    # Initialize Orchestrator
    print("\n[3/3] Initializing Agent Orchestrator...")
    orchestrator = OrchestratorAgent(langfuse_handler)
    print("✓ Orchestrator ready")
    
    print("\n" + "="*50)
    print("System Ready!")
    print("="*50 + "\n")
    
    return orchestrator


def chat_mode(orchestrator):
    """Interactive chat mode"""
    print("Grocery Shopping Chatbot")
    print("Type 'quit' to exit, 'eval' to run evaluation\n")
    
    session_id = f"session_{int(os.urandom(4).hex(), 16)}"
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if user_input.lower() == 'eval':
                evaluator = AutoEvaluator()
                evaluator.run_evaluation(orchestrator)
                continue
            
            # Process input
            result = orchestrator.process(user_input, session_id)
            
            print(f"\nBot ({result['agent']}): {result['response']}\n")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def eval_mode(orchestrator):
    """Evaluation mode"""
    evaluator = AutoEvaluator()
    evaluator.run_evaluation(orchestrator)


def main():
    parser = argparse.ArgumentParser(description="Grocery Shopping Agentic Chatbot")
    parser.add_argument(
        '--mode',
        choices=['chat', 'eval', 'init'],
        default='chat',
        help='Mode to run: chat (interactive), eval (evaluation), init (initialize only)'
    )
    
    args = parser.parse_args()
    
    # Initialize system
    orchestrator = initialize_system()
    
    if args.mode == 'chat':
        chat_mode(orchestrator)
    elif args.mode == 'eval':
        eval_mode(orchestrator)
    elif args.mode == 'init':
        print("Initialization complete. Exiting.")


if __name__ == "__main__":
    main()