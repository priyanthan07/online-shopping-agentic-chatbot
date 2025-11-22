import json
from typing import List, Dict
from langchain_openai import ChatOpenAI
from src.config import MODEL_NAME, DATA_DIR, OPENAI_API_KEY
from src.monitoring.logger import setup_logger
import time

class AutoEvaluator:
    def __init__(self):
        self.llm = ChatOpenAI(model=MODEL_NAME, temperature=0, api_key=OPENAI_API_KEY)
        self.logger = setup_logger(__name__)
        self.ground_truth = self.load_ground_truth()
        self.logger.info("AutoEvaluator initialized")
        
    def load_ground_truth(self) -> List[Dict]:
        """Load ground truth Q&A pairs for evaluation"""
        try:
            with open(DATA_DIR / "eval_qa_pairs.json", 'r') as f:
                data = json.load(f)
                self.logger.info(f"Loaded {len(data)} evaluation test cases")
                return data
        except FileNotFoundError:
            self.logger.warning("eval_qa_pairs.json not found, using default test cases")
            # Return default test cases
            return [
                {
                    "question": "What is your return policy?",
                    "expected_keywords": ["30 days", "refund", "original condition"]
                },
                {
                    "question": "How much does milk cost?",
                    "expected_keywords": ["milk", "price", "$"]
                }
            ]
    def evaluate_response(self, question: str, response: str, expected_keywords: List[str]) -> Dict:
        """Evaluate a single response"""
        self.logger.debug(f"Evaluating response for: {question[:50]}...")
        
        # Calculate keyword match score
        response_lower = response.lower()
        matched_keywords = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
        keyword_score = matched_keywords / len(expected_keywords) if expected_keywords else 0
        
        self.logger.debug(f"Keyword score: {keyword_score:.2f} ({matched_keywords}/{len(expected_keywords)} matched)")
        
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
            llm_eval = self.llm.invoke(eval_prompt).content.strip()
            relevance_score = float(llm_eval)
            self.logger.debug(f"LLM relevance score: {relevance_score:.2f}")
            
        except:
            self.logger.warning(f"Failed to parse LLM evaluation, using default 0.5: {e}")
            relevance_score = 0.5  # Default if parsing fails
        
        # Combined score
        final_score = (keyword_score * 0.3) + (relevance_score * 0.7)
        
        return {
            "question": question,
            "response": response,
            "keyword_score": keyword_score,
            "relevance_score": relevance_score,
            "final_score": final_score,
            "passed": final_score >= 0.6
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

            self.logger.info(f"Test {i}/{len(self.ground_truth)}: {question}")
            
            # Measure latency
            start_time = time.time()
            result = orchestrator.process(question, session_id=f"eval_{i}")
            latency = time.time() - start_time
            total_latency += latency
            
            # Evaluate
            eval_result = self.evaluate_response(
                question,
                result['response'],
                expected_keywords
            )
            eval_result['latency'] = latency
            eval_result['agent_used'] = result.get('agent')
            
            results.append(eval_result)
            
            status = "✓ PASS" if eval_result['passed'] else "✗ FAIL"
            self.logger.info(f"  {status} - Score: {eval_result['final_score']:.2f} - Latency: {latency:.2f}s")
        
        # Calculate aggregate metrics
        passed_tests = sum(1 for r in results if r['passed'])
        avg_score = sum(r['final_score'] for r in results) / len(results)
        avg_latency = total_latency / len(results)
        
        summary = {
            "total_tests": len(results),
            "passed": passed_tests,
            "failed": len(results) - passed_tests,
            "pass_rate": passed_tests / len(results),
            "average_score": avg_score,
            "average_latency": avg_latency,
            "results": results
        }
        
        self.logger.info(f"Evaluation pass rate: {summary['pass_rate']:.2%}")
        self.logger.info(f"Average latency: {avg_latency:.2f}s")
    
        
        # Save detailed results
        results_file = DATA_DIR.parent / "logs" / "evaluation_results.json"
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2)
            
        self.logger.info(f"Evaluation results saved to {results_file}")
        
        return summary