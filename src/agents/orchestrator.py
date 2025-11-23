from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.agents.faq_agent import FAQAgent
from src.agents.action_agent import ActionAgent
from src.guardrails.safety import SafetyGuardrails
from src.monitoring.logger import setup_logger
from src.config import MODEL_NAME, OPENAI_API_KEY
from langfuse.langchain import CallbackHandler
from typing import Dict, Literal,  Optional
from pydantic import BaseModel, Field
import json

class RoutingDecision(BaseModel):
    category: Literal["FAQ", "ACTION", "GENERAL"]
    reasoning: str 

class OrchestratorAgent:
    def __init__(self, langfuse_handler:  Optional[CallbackHandler]):
        self.llm = ChatOpenAI(model=MODEL_NAME, temperature=0, api_key=OPENAI_API_KEY)
        self.faq_agent = FAQAgent(langfuse_handler)
        self.guardrails = SafetyGuardrails()
        self.logger = setup_logger(__name__)
        self.action_agent = ActionAgent(langfuse_handler, self.guardrails)
        self.langfuse_handler = langfuse_handler
        
        self.structured_llm = self.llm.with_structured_output(RoutingDecision)
        
        self.routing_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a routing agent that determines which specialized agent should handle a user request.

                        Analyze the user's message and classify it into one of these categories:

                        1. FAQ: Questions about policies, general information, how things work, delivery, returns policy
                        Examples: "What's your return policy?", "Do you deliver on weekends?", "How do I track my order?"

                        2. ACTION: Requests to perform actions like checking prices, adding to cart, creating refunds, budget calculations
                        Examples: "Add milk to cart", "What's the price of apples?", "Create a refund for order ORD001", "Can I buy these within $50?"

                        3. GENERAL: Greetings, thanks, or simple acknowledgments
                        Examples: "Hello", "Thanks", "Goodbye"

                        Respond with ONLY a JSON object in this exact format:
                        {{"category": "FAQ" | "ACTION" | "GENERAL", "reasoning": "brief explanation"}}"""),
                        ("human", "{input}")
                    ])
        
        self.logger.info("Orchestrator initialized successfully")
        
    def route_request(self, user_input: str) -> str:
        """
            Determine which agent should handle the request
        """
        self.logger.info(f"Routing request: {user_input[:100]}...")
        
        routing_decision = self.structured_llm.invoke(
            self.routing_prompt.format_messages(input=user_input),
            config={"callbacks": [self.langfuse_handler]}
        )
        
        self.logger.info(f"Routed to: {routing_decision.category} - Reason: {routing_decision.reasoning}")
        return routing_decision.category
        
    def process(self, user_input: str, session_id: str = "default") -> Dict:
        """
            Main orchestration logic with guardrails and monitoring
        """
        self.logger.info(f"[Session: {session_id}] Processing request")
        self.logger.info(f"[Session: {session_id}] User input: {user_input}")
        
        agent_used = "unknown"
    
        # Apply safety guardrails
        is_safe, safety_msg = self.guardrails.check_content(user_input)
        if not is_safe:
            self.logger.warning(f"[Session: {session_id}] Content blocked by guardrails")
            result = {
                "response": safety_msg,
                "agent": "GUARDRAILS",
                "blocked": True
            }
            return result
        
        try:
            # Route to appropriate agent
            category = self.route_request(user_input)
            agent_used = category
            
            self.logger.info(f"[Session: {session_id}] Using {agent_used} agent")
            
            if category == "FAQ":
                response = self.faq_agent.answer(user_input)
            elif category == "ACTION":
                response = self.action_agent.execute(user_input)
            else:  # GENERAL
                response = self.llm.invoke(
                    f"Respond briefly and helpfully to this message in the context of a grocery shopping assistant: {user_input}",
                    config={"callbacks": [self.langfuse_handler]}
                ).content
            
            # Sanitize output
            response = self.guardrails.sanitize_output(response)
            
            result = {
                "response": response,
                "agent": agent_used,
                "category": category,
                "blocked": False
            }
            
            self.logger.info(f"[Session: {session_id}] Response generated successfully by {agent_used}")
            self.logger.info(f"[Session: {session_id}] Response: {response[:100]}...")
            
        except Exception as e:
            self.logger.error(f"[Session: {session_id}] Error processing request: {e}", exc_info=True)
            result = {
                "response": f"I apologize, but I encountered an error processing your request. Please try again or rephrase your question.",
                "agent": agent_used,
                "error": str(e),
                "blocked": False
            }
        
        return result
    