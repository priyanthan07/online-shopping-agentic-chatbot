from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from src.agents.faq_agent import FAQAgent
from src.agents.action_agent import ActionAgent
from src.guardrails.safety import SafetyGuardrails
from src.monitoring.logger import ConversationLogger
from src.config import MODEL_NAME
from langfuse.callback import CallbackHandler
from typing import Dict
import json

class OrchestratorAgent:
    def __init__(self, langfuse_handler: CallbackHandler):
        self.llm = ChatOpenAI(model=MODEL_NAME, temperature=0)
        self.faq_agent = FAQAgent(langfuse_handler)
        self.action_agent = ActionAgent(langfuse_handler)
        self.guardrails = SafetyGuardrails()
        self.logger = ConversationLogger()
        self.langfuse_handler = langfuse_handler
        
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
        
    def route_request(self, user_input: str) -> str:
        """
            Determine which agent should handle the request
        """
        response = self.llm.invoke(
            self.routing_prompt.format_messages(input=user_input),
            config={"callbacks": [self.langfuse_handler]}
        )
        
        try:
            # Extract JSON from response
            content = response.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            result = json.loads(content)
            return result['category']
        except:
            # Default to GENERAL if parsing fails
            return "GENERAL"
        
    def process(self, user_input: str, session_id: str = "default") -> Dict:
        """
            Main orchestration logic with guardrails and monitoring
        """
        
        # Apply safety guardrails
        is_safe, safety_msg = self.guardrails.check_content(user_input)
        if not is_safe:
            result = {
                "response": safety_msg,
                "agent": "guardrails",
                "blocked": True
            }
            self.logger.log_conversation(session_id, user_input, result)
            return result
        
        # Route to appropriate agent
        category = self.route_request(user_input)
        
        agent_used = category.lower()
        response = ""
        
        try:
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
            
        except Exception as e:
            result = {
                "response": f"I apologize, but I encountered an error processing your request. Please try again or rephrase your question.",
                "agent": agent_used,
                "error": str(e),
                "blocked": False
            }
        
        # Log conversation
        self.logger.log_conversation(session_id, user_input, result)
        
        return result
    