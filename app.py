#!/usr/bin/env python3
import streamlit as st
import sys
from pathlib import Path
import uuid

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Import from main.py
from src.main import initialize_system, process_user_query, run_evaluation
from src.monitoring.logger import setup_logger

# Setup logger
logger = setup_logger(__name__)


@st.cache_resource
def get_orchestrator():
    """Initialize orchestrator using main.py's initialize_system function"""
    return initialize_system()


def main():
    # Page config
    st.set_page_config(
        page_title="Grocery Shopping Assistant",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        .main {
            padding: 2rem;
        }
        .stChatMessage {
            padding: 1rem;
            border-radius: 0.5rem;
        }
        .chat-header {
            text-align: center;
            padding: 1rem;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 0.5rem;
            margin-bottom: 2rem;
        }
        .agent-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.8rem;
            font-weight: 600;
            margin-top: 0.5rem;
        }
        .agent-faq {
            background-color: #e3f2fd;
            color: #1976d2;
        }
        .agent-action {
            background-color: #f3e5f5;
            color: #7b1fa2;
        }
        .agent-general {
            background-color: #e8f5e9;
            color: #388e3c;
        }
        .agent-guardrails {
            background-color: #ffebee;
            color: #c62828;
        }
        .sidebar-info {
            background-color: #f5f5f5;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
        <div class="chat-header">
            <h1> Grocery Shopping Assistant</h1>
            <p>Your AI-powered shopping companion</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Initialize system using main.py
    with st.spinner(" Initializing chatbot system..."):
        try:
            orchestrator = get_orchestrator()
            st.success(" Chatbot system ready!")
        except Exception as e:
            st.error(f" Failed to initialize system: {str(e)}")
            logger.error(f"Initialization error: {e}", exc_info=True)
            st.stop()
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"streamlit_{uuid.uuid4().hex[:8]}"
    
    if "show_evaluation" not in st.session_state:
        st.session_state.show_evaluation = False
    
    # Sidebar
    with st.sidebar:
        st.title(" Chat Controls")
        
        # Session info
        st.markdown("---")
        st.markdown('<div class="sidebar-info">', unsafe_allow_html=True)
        st.subheader(" Session Info")
        st.text(f"Session ID: {st.session_state.session_id}")
        st.text(f"Messages: {len(st.session_state.messages)}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button(" Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.session_state.session_id = f"streamlit_{uuid.uuid4().hex[:8]}"
                logger.info("Chat cleared by user")
                st.rerun()
        
        with col2:
            if st.button(" Evaluate", use_container_width=True, type="primary"):
                st.session_state.show_evaluation = True
                logger.info("Evaluation triggered by user")
                st.rerun()
        
        st.markdown("---")
        
        # Features
        st.subheader(" Features")
        st.markdown("""
        - **FAQ Support**: Ask about policies, delivery, returns
        - **Shopping Actions**: Add to cart, check prices
        - **Budget Planning**: Calculate within budget
        - **Refund Processing**: Create refund requests
        - **Stock Check**: Real-time inventory via MCP
        - **Safety Guardrails**: Content filtering
        - **Multi-Agent System**: Intelligent routing
        """)
        
        st.markdown("---")
        
        # Example queries
        st.subheader(" Try These Examples")
        example_categories = {
            " FAQ Queries": [
                "What's your return policy?",
                "Do you deliver on weekends?",
                "What payment methods do you accept?",
            ],
            " Shopping Actions": [
                "How much does milk cost?",
                "Can I buy milk and bread for $10?",
                "Check stock for product P001",
            ],
            " Budget & Refunds": [
                "Can I afford rice, chicken, and eggs within $30?",
                "Create a refund for order ORD001",
                "Create a refund for order ORD005",
            ],
            " Edge Cases & Testing": [
                "Check stock for product P007",  # Out of stock
                "Create a refund for ORD999",  # Invalid order
                "I want a refund for order ORD006",  # Exceeds limit
            ]
        }
        
        for category, queries in example_categories.items():
            with st.expander(category):
                for query in queries:
                    if st.button(f" {query}", key=f"example_{hash(query)}", use_container_width=True):
                        st.session_state.example_query = query
                        st.rerun()
    
    # Show evaluation results if requested
    if st.session_state.show_evaluation:
        st.markdown("---")
        st.subheader(" Evaluation Results")
        
        with st.spinner("Running evaluation tests..."):
            # Use main.py's run_evaluation function
            summary = run_evaluation(orchestrator)
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Pass Rate", f"{summary['pass_rate']*100:.1f}%")
            with col2:
                st.metric("Tests Passed", f"{summary['passed']}/{summary['total_tests']}")
            with col3:
                st.metric("Avg Score", f"{summary['average_score']:.2f}")
            with col4:
                st.metric("Avg Latency", f"{summary['average_latency']:.2f}s")
            
            # Show individual results
            with st.expander(" Detailed Test Results"):
                for i, result in enumerate(summary['results'], 1):
                    status_icon = "" if result['passed'] else ""
                    st.markdown(f"**Test {i}:** {status_icon} {result['question']}")
                    st.text(f"Score: {result['final_score']:.2f} | Agent: {result['agent_used']} | Latency: {result['latency']:.2f}s")
                    st.text(f"Response: {result['response'][:100]}...")
                    st.markdown("---")
        
        # Button to close evaluation
        if st.button(" Close Evaluation"):
            st.session_state.show_evaluation = False
            st.rerun()
        
        st.markdown("---")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show agent badge for assistant messages
            if message["role"] == "assistant" and "agent" in message:
                agent = message["agent"]
                agent_class = f"agent-{agent}"
                st.markdown(
                    f'<span class="agent-badge {agent_class}"> Agent: {agent.upper()}</span>',
                    unsafe_allow_html=True
                )
    
    # Handle example query from sidebar
    if "example_query" in st.session_state:
        user_input = st.session_state.example_query
        del st.session_state.example_query
    else:
        user_input = st.chat_input(" Type your message here...")
    
    # Process user input
    if user_input:
        logger.info(f"User input received: {user_input[:50]}...")
        
        # Add user message to chat
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Get bot response
        with st.chat_message("assistant"):
            with st.spinner(" Thinking..."):
                
                result = process_user_query(
                    orchestrator, 
                    user_input, 
                    st.session_state.session_id
                )
                
                # Extract response and metadata
                response = result.get("response", "I apologize, but I couldn't process your request.")
                agent = result.get("agent", "unknown")
                blocked = result.get("blocked", False)
                
                # Display response
                st.markdown(response)
                
                # Show agent badge
                agent_class = f"agent-{agent}"
                st.markdown(
                    f'<span class="agent-badge {agent_class}"> Agent: {agent.upper()}</span>',
                    unsafe_allow_html=True
                )
                
                # Add to message history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "agent": agent,
                    "blocked": blocked
                })
                
                logger.info(f"Response generated by {agent} agent")


if __name__ == "__main__":
    main()