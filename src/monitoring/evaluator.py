import json
from typing import List, Dict
from langchain_openai import ChatOpenAI
from src.config import MODEL_NAME, DATA_DIR, OPENAI_API_KEY
from src.monitoring.logger import setup_logger
import time
from pydantic import BaseModel

class EvalScore(BaseModel):
    score: float
    reasoning: str 

class AutoEvaluator:
    def __init__(self):
        self.llm = ChatOpenAI(model=MODEL_NAME, temperature=0, api_key=OPENAI_API_KEY)
        self.logger = setup_logger(__name__)
        self.ground_truth = self.load_ground_truth()
        self.structured_llm = self.llm.with_structured_output(EvalScore)
        self.logger.info("AutoEvaluator initialized")
        
    def load_ground_truth(self) -> List[Dict]:
        """Load ground truth Q&A pairs for evaluation"""
        try:
            with open(DATA_DIR / "eval_qa_pairs.json", 'r') as f:
                data = json.load(f)
                self.logger.info(f"Loaded {len(data)} evaluation test cases")
                return data
        except FileNotFoundError:
            self.logger.error("eval_qa_pairs.json not found, using default test cases")
            return []
        
    def evaluate_response(self, question: str, response: str, expected_keywords: List[str], 
                         should_block: bool, was_blocked: bool, expected_agent: str, actual_agent: str) -> Dict:
        """Evaluate a single response with blocking validation"""
        self.logger.info(f"Evaluating response for: {question[:50]}...")
        
        # For guardrail tests, blocking behavior is primary
        if should_block:
            if was_blocked:
                self.logger.info(f"Guardrail test PASSED - Content correctly blocked")
                # Check if agent is "guardrails"
                agent_correct = (actual_agent == "guardrails")
                
                return {
                    "question": question,
                    "response": response,
                    "keyword_score": 1.0 if agent_correct else 0.5,
                    "relevance_score": 1.0,
                    "final_score": 1.0 if agent_correct else 0.7,
                    "passed": agent_correct,
                    "blocking_correct": True,
                    "agent_correct": agent_correct
                }
            else:
                self.logger.warning(f"Guardrail test FAILED - Content should have been blocked but wasn't")
                return {
                    "question": question,
                    "response": response,
                    "keyword_score": 0.0,
                    "relevance_score": 0.0,
                    "final_score": 0.0,
                    "passed": False,
                    "blocking_correct": False,
                    "agent_correct": False
                }
        
        # For non-guardrail tests, use standard evaluation
        # Calculate keyword match score
        response_lower = response.lower()
        matched_keywords = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
        keyword_score = matched_keywords / len(expected_keywords) if expected_keywords else 0
        
        self.logger.info(f"Keyword score: {keyword_score:.2f} ({matched_keywords}/{len(expected_keywords)} matched)")
        
        # Check agent routing
        agent_correct = (actual_agent.upper() == expected_agent.upper())
        self.logger.info(f"Agent routing: expected={expected_agent}, actual={actual_agent}, correct={agent_correct}")
        
        # Use LLM to evaluate relevance
        eval_prompt = f"""Evaluate if this response adequately answers the question.
        
                            Question: {question}
                            Response: {response}

                            Rate the response on a scale of 0-1 where:
                            - 1.0 = Perfect, complete answer
                            - 0.7-0.9 = Good answer with minor issues
                            - 0.4-0.6 = Partial answer
                            - 0.0-0.3 = Poor or irrelevant answer

                            Respond with ONLY a number between 0 and 1.
                        """
        
        try:
            llm_eval = self.structured_llm.invoke(eval_prompt)
            relevance_score = float(llm_eval.score)
            self.logger.info(f"LLM relevance score: {relevance_score:.2f} and reason: {llm_eval.reasoning}")
            
        except Exception as e:
            self.logger.warning(f"Failed to parse LLM evaluation, using default 0.5: {e}")
            relevance_score = 0.5
        
        # Combined score with agent routing weight
        final_score = (keyword_score * 0.2) + (relevance_score * 0.6) + (0.2 if agent_correct else 0.0)
        
        return {
            "question": question,
            "response": response,
            "keyword_score": keyword_score,
            "relevance_score": relevance_score,
            "final_score": final_score,
            "passed": final_score >= 0.6,
            "blocking_correct": not was_blocked,
            "agent_correct": agent_correct
        }
    
    def run_evaluation(self, orchestrator) -> Dict:
        """Run full evaluation suite"""
        self.logger.info("="*50)
        self.logger.info("Starting Evaluation Suite")
        self.logger.info("="*50)
        
        results = []
        total_latency = 0
        
        for i, test_case in enumerate(self.ground_truth, 1):
            question = test_case['question']
            expected_keywords = test_case.get('expected_keywords', [])
            should_block = test_case.get('should_block', False)
            expected_agent = test_case.get('expected_agent', 'UNKNOWN')

            self.logger.info(f"Test {i}/{len(self.ground_truth)}: {question}")
            
            # Measure latency
            start_time = time.time()
            result = orchestrator.process(question, session_id=f"eval_{i}")
            latency = time.time() - start_time
            total_latency += latency
            
            # Extract actual values
            was_blocked = result.get('blocked', False)
            actual_agent = result.get('agent', 'unknown')
            
            # Evaluate
            eval_result = self.evaluate_response(
                question,
                result['response'],
                expected_keywords,
                should_block,
                was_blocked,
                expected_agent,
                actual_agent
            )
            eval_result['latency'] = latency
            eval_result['agent_used'] = actual_agent
            eval_result['expected_agent'] = expected_agent
            eval_result['should_block'] = should_block
            eval_result['was_blocked'] = was_blocked
            
            results.append(eval_result)
            
            status = "[PASS]" if eval_result['passed'] else "[FAIL]"
            self.logger.info(f"  {status} - Score: {eval_result['final_score']:.2f} - Latency: {latency:.2f}s")
            
            # Log blocking validation
            if should_block:
                block_status = "[BLOCKED]" if was_blocked else "[NOT BLOCKED]"
                self.logger.info(f"    Blocking: Expected=True, Actual={was_blocked} {block_status}")
        
        # Calculate aggregate metrics
        passed_tests = sum(1 for r in results if r['passed'])
        avg_score = sum(r['final_score'] for r in results) / len(results)
        avg_latency = total_latency / len(results)
        
        # Calculate blocking accuracy
        guardrail_tests = [r for r in results if r['should_block']]
        blocking_accuracy = sum(1 for r in guardrail_tests if r['blocking_correct']) / len(guardrail_tests) if guardrail_tests else 1.0
        
        # Calculate agent routing accuracy
        agent_accuracy = sum(1 for r in results if r['agent_correct']) / len(results)
        
        summary = {
            "total_tests": len(results),
            "passed": passed_tests,
            "failed": len(results) - passed_tests,
            "pass_rate": passed_tests / len(results),
            "average_score": avg_score,
            "average_latency": avg_latency,
            "blocking_accuracy": blocking_accuracy,
            "agent_routing_accuracy": agent_accuracy,
            "results": results
        }
        
        self.logger.info("="*50)
        self.logger.info("EVALUATION SUMMARY")
        self.logger.info("="*50)
        self.logger.info(f"Pass rate: {summary['pass_rate']:.2%}")
        self.logger.info(f"Agent routing accuracy: {agent_accuracy:.2%}")
        self.logger.info(f"Blocking accuracy: {blocking_accuracy:.2%}")
        self.logger.info(f"Average latency: {avg_latency:.2f}s")
        self.logger.info("="*50)
        
        # Save detailed results
        results_file = DATA_DIR.parent / "logs" / "evaluation_results.json"
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2)
            
        self.logger.info(f"Evaluation results saved to {results_file}")
        
        return summary