from typing import Dict, Tuple
from src.config import MAX_REFUND_AMOUNT, RESTRICTED_TOPICS
import json
import re

class SafetyGuardrails:
    def __init__(self):
        self.max_refund = MAX_REFUND_AMOUNT
        self.restricted_topics = RESTRICTED_TOPICS
        
    def check_content(self, message: str) -> Tuple[bool, str]:
        """
            Check if message contains restricted content
        """
        message_lower = message.lower()
        
        for topic in self.restricted_topics:
            if topic in message_lower:
                return False, f"Sorry, I cannot discuss topics related to {topic}. I'm here to help with grocery shopping."
            
        # Check for malicious patterns
        malicious_patterns = [
            r'<script',
            r'javascript:',
            r'eval\(',
            r'__import__',
        ]
        
        for pattern in malicious_patterns:
            if re.search(pattern, message_lower):
                return False, "Invalid input detected. Please rephrase your request."
        return True, ""
    
    def validate_refund(self, tool_input: str) -> Tuple[bool, str]:
        """
            Validate refund requests
        """
        try:
            # Extract amount if present in refund tool call
            if "amount" in tool_input.lower():
                # Parse potential JSON
                try:
                    data = json.loads(tool_input)
                    amount = data.get("amount", 0)
                except:
                    # Try to extract number
                    import re
                    amounts = re.findall(r'\$?(\d+\.?\d*)', tool_input)
                    amount = float(amounts[0]) if amounts else 0
                
                if amount > self.max_refund:
                    return False, f"Refund amount ${amount} exceeds maximum allowed refund of ${self.max_refund}. Please contact customer service."
            
            return True, ""
        
        except Exception as e:
            return True, ""
    
    def validate_tool_call(self, tool_name: str, tool_input: str) -> Tuple[bool, str]:
        """
            Validate tool calls before execution
        """
        
        if tool_name == "create_refund":
            return self.validate_refund(tool_input)
        
        
        return True, ""
    
    def sanitize_output(self, output: str) -> str:
        """
            Sanitize agent output
        """
        sanitized = output
        
        # Remove email patterns (example)
        sanitized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', sanitized)
        
        return sanitized
    