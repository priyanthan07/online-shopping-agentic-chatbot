import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from src.config import LOGS_DIR


class ConversationLogger:
    def __init__(self):
        self.log_file = LOGS_DIR / f"conversations_{datetime.now().strftime('%Y%m%d')}.jsonl"
        self.metrics_file = LOGS_DIR / "metrics.json"
        
    def log_conversation(self, session_id: str, user_input: str, result: Dict):
        """Log a conversation turn"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "user_input": user_input,
            "agent": result.get("agent"),
            "category": result.get("category"),
            "response": result.get("response"),
            "blocked": result.get("blocked", False),
            "error": result.get("error")
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def log_tool_call(self, session_id: str, tool_name: str, tool_input: str, result: str):
        """Log tool usage"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "type": "tool_call",
            "tool_name": tool_name,
            "tool_input": tool_input,
            "result": result
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def get_conversations(self, session_id: str = None) -> List[Dict]:
        """Retrieve conversation logs"""
        conversations = []
        
        if not self.log_file.exists():
            return conversations
        
        with open(self.log_file, 'r') as f:
            for line in f:
                entry = json.loads(line)
                if session_id is None or entry.get("session_id") == session_id:
                    conversations.append(entry)
        
        return conversations
    
    def update_metrics(self, metric_name: str, value: float):
        """Update metrics"""
        metrics = {}
        
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r') as f:
                metrics = json.load(f)
        
        if metric_name not in metrics:
            metrics[metric_name] = []
        
        metrics[metric_name].append({
            "timestamp": datetime.now().isoformat(),
            "value": value
        })
        
        with open(self.metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)