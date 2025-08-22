#!/usr/bin/env python3
"""
LM Studio Evaluator Script with RAG Support

This script evaluates user inputs against expected outputs using 
LM Studio server with the gpt-oss-20b-mlx model and RAG capabilities.
"""

import json
import time
import logging
import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import requests
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('evaluator.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TestRun:
    """Represents a single run of a test case"""
    run_number: int
    timestamp: str
    response: str

@dataclass
class TestCase:
    """Represents a test case with multiple runs"""
    test_id: str
    input_text: str
    reference_output: str
    runs: List[TestRun]

@dataclass
class DetailedScores:
    """Detailed scoring breakdown"""
    factual_accuracy: int
    completeness: int
    order_sequence: int
    relevance: int
    overall_quality: int
    
@dataclass
class RunEvaluationResult:
    """Represents the result of evaluating a single run"""
    test_case: TestCase
    test_run: TestRun
    evaluation: str  # CORRECT, INCORRECT, or PARTIAL
    detailed_scores: DetailedScores
    rag_verification: str
    reasoning: str
    recommendation: str
    processing_time: float
    success: bool
    
    @property
    def average_score(self) -> float:
        """Calculate weighted average score with Factual Accuracy at 60%"""
        # Weighted scoring: Factual Accuracy 60%, others 10% each
        weighted_score = (
            self.detailed_scores.factual_accuracy * 0.60 +  # 60%
            self.detailed_scores.completeness * 0.10 +       # 10%
            self.detailed_scores.order_sequence * 0.10 +     # 10%
            self.detailed_scores.relevance * 0.10 +          # 10%
            self.detailed_scores.overall_quality * 0.10      # 10%
        )
        return weighted_score

@dataclass 
class TestCaseResult:
    """Represents the aggregated results for all runs of a test case"""
    test_case: TestCase
    run_results: List[RunEvaluationResult]
    
    @property
    def average_score_across_runs(self) -> float:
        """Calculate average score across all runs"""
        if not self.run_results:
            return 0.0
        return sum(result.average_score for result in self.run_results) / len(self.run_results)
    
    @property
    def best_run_score(self) -> float:
        """Get the best score among all runs"""
        if not self.run_results:
            return 0.0
        return max(result.average_score for result in self.run_results)
    
    @property
    def worst_run_score(self) -> float:
        """Get the worst score among all runs"""
        if not self.run_results:
            return 0.0
        return min(result.average_score for result in self.run_results)

class LMStudioEvaluator:
    """Main evaluator class for LM Studio integration"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the evaluator with configuration"""
        self.config = self._load_config(config_path)
        self.client = self._initialize_client()
        self.prompt_template = self._load_prompt_template()
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file {config_path} not found")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise
    
    def _initialize_client(self) -> OpenAI:
        """Initialize OpenAI client for LM Studio"""
        try:
            client = OpenAI(
                base_url=self.config["lm_studio"]["base_url"],
                api_key=self.config["lm_studio"]["api_key"] or "not-needed"
            )
            logger.info(f"LM Studio client initialized: {self.config['lm_studio']['base_url']}")
            return client
        except Exception as e:
            logger.error(f"Failed to initialize LM Studio client: {e}")
            raise
    
    def _load_prompt_template(self) -> str:
        """Load the evaluation prompt template"""
        try:
            # Use system_prompt.txt instead of evaluation_prompt.txt
            prompt_file = "system_prompt.txt"
            with open(prompt_file, 'r') as f:
                template = f.read()
            logger.info(f"System prompt loaded from {prompt_file}")
            return template
        except FileNotFoundError:
            logger.error(f"System prompt file {prompt_file} not found")
            raise
    
    def _check_server_health(self) -> bool:
        """Check if LM Studio server is responding"""
        try:
            base_url = self.config["lm_studio"]["base_url"].replace("/v1", "")
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("LM Studio server is healthy")
                return True
            else:
                logger.warning(f"LM Studio server returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Cannot connect to LM Studio server: {e}")
            return False
    
    def _create_evaluation_prompt(self, test_case: TestCase, test_run: TestRun) -> str:
        """Create the evaluation prompt for a specific test case run"""
        # The system prompt is used as system message, user message contains the evaluation request
        evaluation_request = f"""Now evaluate the following:
Input: {test_case.input_text}
Reference Behavior: {test_case.reference_output}
Actual Output (Run {test_run.run_number}): {test_run.response}
Timestamp: {test_run.timestamp}

Begin evaluation:"""
        
        return evaluation_request
    
    def _get_model_response(self, input_text: str) -> str:
        """Get response from the model for given input"""
        try:
            # Add RAG instruction if enabled
            rag_instruction = ""
            if self.config["rag"]["enabled"]:
                rag_instruction = " Use your knowledge base and available tools to provide accurate, well-researched answers."
            
            messages = [
                {
                    "role": "system", 
                    "content": f"You are a helpful assistant with access to a knowledge base. Reasoning: {self.config['model_parameters']['reasoning_level']}.{rag_instruction}"
                },
                {"role": "user", "content": input_text}
            ]
            
            # Prepare tools if RAG is enabled
            request_params = {
                "model": self.config["lm_studio"]["model_name"],
                "messages": messages,
                "temperature": self.config["model_parameters"]["temperature"],
                "max_tokens": self.config["model_parameters"]["max_tokens"],
                "top_p": self.config["model_parameters"]["top_p"],
                "frequency_penalty": self.config["model_parameters"]["frequency_penalty"],
                "presence_penalty": self.config["model_parameters"]["presence_penalty"]
            }
            
            # Add tools for RAG if enabled (LM Studio uses tools parameter)
            if self.config["rag"]["enabled"] and self.config["rag"]["use_tools"]:
                request_params["tools"] = [
                    {
                        "type": "function",
                        "function": {
                            "name": "search_knowledge_base",
                            "description": "Search the knowledge base for factual information",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "The search query for the knowledge base"
                                    }
                                },
                                "required": ["query"]
                            }
                        }
                    }
                ]
                request_params["tool_choice"] = "auto"
            
            response = self.client.chat.completions.create(**request_params)
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error getting model response: {e}")
            raise
    
    def _evaluate_response(self, test_case: TestCase, test_run: TestRun) -> tuple[str, DetailedScores, str, str, str]:
        """Evaluate the model's response against expected output with detailed breakdown"""
        try:
            evaluation_prompt = self._create_evaluation_prompt(test_case, test_run)
            
            messages = [
                {"role": "system", "content": self.prompt_template},
                {"role": "user", "content": evaluation_prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.config["lm_studio"]["model_name"],
                messages=messages,
                temperature=0.1,  # Lower temperature for more consistent evaluation
                max_tokens=1500  # Increased for detailed response
            )
            
            evaluation_text = response.choices[0].message.content.strip()
            
            # Parse structured response
            return self._parse_structured_evaluation(evaluation_text)
            
        except Exception as e:
            logger.error(f"Error during evaluation: {e}")
            default_scores = DetailedScores(0, 0, 0, 0, 0)
            return "ERROR", default_scores, "", f"Evaluation failed: {str(e)}", "Fix technical issues"
    
    def _parse_structured_evaluation(self, evaluation_text: str) -> tuple[str, DetailedScores, str, str, str]:
        """Parse the structured evaluation response"""
        import re
        
        # Default values
        evaluation = "INCORRECT"
        scores = DetailedScores(0, 0, 0, 0, 0)
        rag_verification = ""
        reasoning = ""
        recommendation = ""
        
        try:
            # Extract evaluation result
            eval_match = re.search(r'EVALUATION_RESULT:\s*(\w+)', evaluation_text, re.IGNORECASE)
            if eval_match:
                evaluation = eval_match.group(1).upper()
            
            # Extract detailed scores
            factual_match = re.search(r'Factual_Accuracy:\s*(\d+)', evaluation_text, re.IGNORECASE)
            completeness_match = re.search(r'Completeness:\s*(\d+)', evaluation_text, re.IGNORECASE)
            order_match = re.search(r'Order_Sequence:\s*(\d+)', evaluation_text, re.IGNORECASE)
            relevance_match = re.search(r'Relevance:\s*(\d+)', evaluation_text, re.IGNORECASE)
            overall_match = re.search(r'Overall_Quality:\s*(\d+)', evaluation_text, re.IGNORECASE)
            
            scores = DetailedScores(
                factual_accuracy=int(factual_match.group(1)) if factual_match else 0,
                completeness=int(completeness_match.group(1)) if completeness_match else 0,
                order_sequence=int(order_match.group(1)) if order_match else 0,
                relevance=int(relevance_match.group(1)) if relevance_match else 0,
                overall_quality=int(overall_match.group(1)) if overall_match else 0
            )
            
            # Verify evaluation consistency with numerical scores
            avg_score = scores.average_score
            if avg_score >= 7 and evaluation not in ["CORRECT"]:
                logger.warning(f"Score {avg_score:.1f} suggests CORRECT but got {evaluation}. Adjusting to CORRECT.")
                evaluation = "CORRECT"
            elif 4 <= avg_score < 7 and evaluation not in ["PARTIAL"]:
                logger.warning(f"Score {avg_score:.1f} suggests PARTIAL but got {evaluation}. Adjusting to PARTIAL.")
                evaluation = "PARTIAL"
            elif avg_score < 4 and evaluation not in ["INCORRECT"]:
                logger.warning(f"Score {avg_score:.1f} suggests INCORRECT but got {evaluation}. Adjusting to INCORRECT.")
                evaluation = "INCORRECT"
            
            # Extract RAG verification section
            rag_match = re.search(r'RAG_VERIFICATION:(.*?)REASONING:', evaluation_text, re.DOTALL | re.IGNORECASE)
            if rag_match:
                rag_verification = rag_match.group(1).strip()
            
            # Extract reasoning section
            reasoning_match = re.search(r'REASONING:(.*?)RECOMMENDATION:', evaluation_text, re.DOTALL | re.IGNORECASE)
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
            
            # Extract recommendation section
            rec_match = re.search(r'RECOMMENDATION:(.*?)$', evaluation_text, re.DOTALL | re.IGNORECASE)
            if rec_match:
                recommendation = rec_match.group(1).strip()
            
        except Exception as e:
            logger.warning(f"Error parsing structured evaluation: {e}")
            reasoning = evaluation_text  # Fallback to full text
        
        return evaluation, scores, rag_verification, reasoning, recommendation
    
    def evaluate_single_run(self, test_case: TestCase, test_run: TestRun) -> RunEvaluationResult:
        """Evaluate a single run of a test case"""
        start_time = time.time()
        
        try:
            logger.info(f"Processing test case {test_case.test_id}, Run {test_run.run_number}")
            
            # Evaluate the response with detailed breakdown
            evaluation, detailed_scores, rag_verification, reasoning, recommendation = self._evaluate_response(test_case, test_run)
            
            processing_time = time.time() - start_time
            success = True
            
            result = RunEvaluationResult(
                test_case=test_case,
                test_run=test_run,
                evaluation=evaluation,
                detailed_scores=detailed_scores,
                rag_verification=rag_verification,
                reasoning=reasoning,
                recommendation=recommendation,
                processing_time=processing_time,
                success=success
            )
            
            logger.info(f"Run {test_run.run_number} completed: {evaluation} (Avg Score: {result.average_score:.1f}/10) ({processing_time:.2f}s)")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Run {test_run.run_number} failed: {e}")
            
            default_scores = DetailedScores(0, 0, 0, 0, 0)
            return RunEvaluationResult(
                test_case=test_case,
                test_run=test_run,
                evaluation="ERROR",
                detailed_scores=default_scores,
                rag_verification="",
                reasoning=f"Test execution failed: {str(e)}",
                recommendation="Fix technical issues and retry",
                processing_time=processing_time,
                success=False
            )
    
    def evaluate_test_case(self, test_case: TestCase) -> TestCaseResult:
        """Evaluate all runs of a test case"""
        logger.info(f"Evaluating test case {test_case.test_id} with {len(test_case.runs)} runs")
        
        run_results = []
        
        for test_run in test_case.runs:
            result = self.evaluate_single_run(test_case, test_run)
            run_results.append(result)
            
            # Add delay between runs to avoid overwhelming the system
            delay = self.config["evaluation"]["delay_between_tests"]
            if delay > 0 and test_run != test_case.runs[-1]:  # Don't delay after last run
                logger.debug(f"Waiting {delay}s before next run...")
                time.sleep(delay)
        
        return TestCaseResult(
            test_case=test_case,
            run_results=run_results
        )
    
    def evaluate_batch(self, test_cases: List[TestCase]) -> List[TestCaseResult]:
        """Evaluate multiple test cases sequentially with progressive reporting"""
        if not self._check_server_health():
            raise ConnectionError("LM Studio server is not available")
        
        total_runs = sum(len(tc.runs) for tc in test_cases)
        logger.info(f"Starting batch evaluation of {len(test_cases)} test cases with {total_runs} total runs")
        results = []
        delay = self.config["evaluation"]["delay_between_tests"]
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"Processing test case {i}/{len(test_cases)}: {test_case.test_id}")
            
            # Add delay between test cases to avoid overwhelming the system
            if i > 1 and delay > 0:
                logger.debug(f"Waiting {delay}s before next test case...")
                time.sleep(delay)
            
            result = self.evaluate_test_case(test_case)
            results.append(result)
            
            # Progressive report update after each test case
            self.update_progressive_report(results, i, len(test_cases))
        
        logger.info(f"Batch evaluation completed: {len(results)} test cases evaluated")
        return results
    
    def parse_user_test_data(self, file_path: str = "user_test_data.txt") -> List[TestCase]:
        """Parse the user test data file into TestCase objects"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            test_cases = []
            lines = content.split('\n')
            i = 0
            
            while i < len(lines):
                line = lines[i].strip()
                
                # Look for "Test Case" followed by a number
                if line == "Test Case" and i + 1 < len(lines):
                    test_id = lines[i + 1].strip()
                    i += 2
                    
                    # Parse Input
                    if i < len(lines) and lines[i].strip() == "Input":
                        i += 1
                        input_text = lines[i].strip() if i < len(lines) else ""
                        i += 1
                    else:
                        input_text = ""
                    
                    # Parse Reference
                    if i < len(lines) and lines[i].strip() == "Reference":
                        i += 1
                        reference_output = lines[i].strip() if i < len(lines) else ""
                        i += 1
                    else:
                        reference_output = ""
                    
                    # Parse Runs
                    runs = []
                    while i < len(lines):
                        line = lines[i].strip()
                        if line.startswith("Run "):
                            try:
                                run_number = int(line.split()[1])
                                i += 1
                                
                                # Skip empty line
                                if i < len(lines) and lines[i].strip() == "":
                                    i += 1
                                
                                # Get timestamp
                                timestamp = lines[i].strip() if i < len(lines) else ""
                                i += 1
                                
                                # Get response (might be multi-line)
                                response_lines = []
                                while i < len(lines):
                                    next_line = lines[i].strip()
                                    if next_line.startswith("Run ") or next_line == "Test Case":
                                        break
                                    if next_line:  # Skip empty lines
                                        response_lines.append(next_line)
                                    i += 1
                                
                                response = " ".join(response_lines)
                                
                                runs.append(TestRun(
                                    run_number=run_number,
                                    timestamp=timestamp,
                                    response=response
                                ))
                                
                                # Don't increment i here as we're already at the next section
                                continue
                                
                            except (ValueError, IndexError):
                                i += 1
                                continue
                        elif line == "Test Case":
                            # Start of next test case
                            break
                        else:
                            i += 1
                    
                    if runs:  # Only add test case if it has runs
                        test_cases.append(TestCase(
                            test_id=test_id,
                            input_text=input_text,
                            reference_output=reference_output,
                            runs=runs
                        ))
                else:
                    i += 1
            
            logger.info(f"Parsed {len(test_cases)} test cases from {file_path}")
            return test_cases
            
        except FileNotFoundError:
            logger.error(f"Test data file {file_path} not found")
            raise
        except Exception as e:
            logger.error(f"Error parsing test data: {e}")
            raise
    
    def print_results_summary(self, results: List[TestCaseResult]):
        """Print a comprehensive table summary of evaluation results with multiple runs"""
        total_test_cases = len(results)
        total_runs = sum(len(tc.run_results) for tc in results)
        successful_runs = sum(1 for tc in results for run in tc.run_results if run.success)
        
        # Count results by type across all runs
        correct_runs = sum(1 for tc in results for run in tc.run_results if run.evaluation == "CORRECT")
        partial_runs = sum(1 for tc in results for run in tc.run_results if run.evaluation == "PARTIAL")
        incorrect_runs = sum(1 for tc in results for run in tc.run_results if run.evaluation == "INCORRECT")
        error_runs = sum(1 for tc in results for run in tc.run_results if run.evaluation == "ERROR")
        
        # Calculate averages
        all_run_times = [run.processing_time for tc in results for run in tc.run_results]
        avg_time = sum(all_run_times) / len(all_run_times) if all_run_times else 0
        
        successful_run_scores = [run.average_score for tc in results for run in tc.run_results if run.success]
        avg_score = sum(successful_run_scores) / len(successful_run_scores) if successful_run_scores else 0
        
        # Print summary statistics
        print("\n" + "="*140)
        print("COMPREHENSIVE EVALUATION SUMMARY - MULTI-RUN ANALYSIS")
        print("="*140)
        print(f"📊 Test Cases: {total_test_cases} | Total Runs: {total_runs}")
        print(f"✅ Correct: {correct_runs} | ⚠️ Partial: {partial_runs} | ❌ Incorrect: {incorrect_runs} | 🚫 Errors: {error_runs}")
        print(f"⏱️ Average Time: {avg_time:.2f}s | 📈 Success Rate: {(correct_runs/total_runs)*100:.1f}% | 🎯 Average Score: {avg_score:.1f}/10")
        print("="*140)
        
        # Print table header
        print("\n📋 DETAILED RESULTS TABLE")
        print("-"*140)
        header = f"{'ID':<8} {'Run':<4} {'Result':<10} {'Fact':<5} {'Comp':<5} {'Order':<5} {'Rel':<5} {'Qual':<5} {'W.Avg':<5} {'Time':<6} {'Input':<40}"
        print(header)
        print("-"*140)
        
        # Print each result row
        for tc_result in results:
            test_id = tc_result.test_case.test_id[:7]  # Truncate if too long
            input_preview = tc_result.test_case.input_text[:38] + "..." if len(tc_result.test_case.input_text) > 38 else tc_result.test_case.input_text
            
            for run_result in tc_result.run_results:
                # Status emoji
                status_emoji = {
                    "CORRECT": "✅",
                    "PARTIAL": "⚠️", 
                    "INCORRECT": "❌",
                    "ERROR": "🚫"
                }.get(run_result.evaluation, "❓")
                
                result_display = f"{status_emoji} {run_result.evaluation[:7]}"
                
                if run_result.success:
                    scores = run_result.detailed_scores
                    row = f"{test_id:<8} {run_result.test_run.run_number:<4} {result_display:<10} {scores.factual_accuracy:<5} {scores.completeness:<5} {scores.order_sequence:<5} {scores.relevance:<5} {scores.overall_quality:<5} {run_result.average_score:<5.1f} {run_result.processing_time:<6.1f} {input_preview:<40}"
                else:
                    row = f"{test_id:<8} {run_result.test_run.run_number:<4} {result_display:<10} {'N/A':<5} {'N/A':<5} {'N/A':<5} {'N/A':<5} {'N/A':<5} {'N/A':<5} {run_result.processing_time:<6.1f} {input_preview:<40}"
                
                print(row)
        
        print("-"*140)
        print("📝 Legend: Fact=Factual Accuracy (60%), Comp=Completeness (10%), Order=Order/Sequence (10%), Rel=Relevance (10%), Qual=Overall Quality (10%)")
        print("📊 W.Avg = Weighted Average Score (Factual Accuracy has 60% weight)")
        print("-"*140)
        
        # Print test case summaries
        print(f"\n📊 TEST CASE SUMMARIES")
        print("="*140)
        
        for tc_result in results:
            print(f"\n🧪 Test Case: {tc_result.test_case.test_id}")
            print(f"📥 Input: {tc_result.test_case.input_text}")
            print(f"📋 Reference: {tc_result.test_case.reference_output}")
            print(f"🔄 Runs: {len(tc_result.run_results)}")
            print(f"📈 Average Score: {tc_result.average_score_across_runs:.1f}/10")
            print(f"🏆 Best Run: {tc_result.best_run_score:.1f}/10")
            print(f"📉 Worst Run: {tc_result.worst_run_score:.1f}/10")
            
            # Show individual runs
            for run_result in tc_result.run_results:
                print(f"   Run {run_result.test_run.run_number}: {run_result.evaluation} ({run_result.average_score:.1f}/10) - {run_result.test_run.timestamp}")
                print(f"   Response: {run_result.test_run.response[:100]}...")
                if run_result.reasoning:
                    print(f"   Reasoning: {run_result.reasoning[:150]}...")
                print()
            
            print("─" * 80)
    
    def export_results_to_csv(self, results: List[TestCaseResult], filename: str = "evaluation_results.csv"):
        """Export results to CSV format for easy analysis with multi-run support"""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'test_id', 'run_number', 'timestamp', 'evaluation', 'factual_accuracy', 'completeness', 
                'order_sequence', 'relevance', 'overall_quality', 'average_score',
                'processing_time', 'input', 'reference_output', 'actual_output',
                'rag_verification', 'reasoning', 'recommendation', 'success'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for tc_result in results:
                for run_result in tc_result.run_results:
                    row = {
                        'test_id': tc_result.test_case.test_id,
                        'run_number': run_result.test_run.run_number,
                        'timestamp': run_result.test_run.timestamp,
                        'evaluation': run_result.evaluation,
                        'processing_time': run_result.processing_time,
                        'input': tc_result.test_case.input_text,
                        'reference_output': tc_result.test_case.reference_output,
                        'actual_output': run_result.test_run.response,
                        'success': run_result.success
                    }
                    
                    if run_result.success and run_result.detailed_scores:
                        row.update({
                            'factual_accuracy': run_result.detailed_scores.factual_accuracy,
                            'completeness': run_result.detailed_scores.completeness,
                            'order_sequence': run_result.detailed_scores.order_sequence,
                            'relevance': run_result.detailed_scores.relevance,
                            'overall_quality': run_result.detailed_scores.overall_quality,
                            'average_score': run_result.average_score,
                            'rag_verification': run_result.rag_verification,
                            'reasoning': run_result.reasoning,
                            'recommendation': run_result.recommendation
                        })
                    else:
                        row.update({
                            'factual_accuracy': 0,
                            'completeness': 0,
                            'order_sequence': 0,
                            'relevance': 0,
                            'overall_quality': 0,
                            'average_score': 0,
                            'rag_verification': '',
                            'reasoning': run_result.reasoning if hasattr(run_result, 'reasoning') else '',
                            'recommendation': run_result.recommendation if hasattr(run_result, 'recommendation') else ''
                        })
                    
                    writer.writerow(row)
        
        logger.info(f"Multi-run results exported to {filename}")
    
    def generate_final_report(self, results: List[TestCaseResult], filename: str = "evaluation_report.md"):
        """Generate a comprehensive final report in Markdown format"""
        from datetime import datetime
        
        # Calculate statistics
        total_test_cases = len(results)
        total_runs = sum(len(tc.run_results) for tc in results)
        successful_runs = sum(1 for tc in results for run in tc.run_results if run.success)
        
        correct_runs = sum(1 for tc in results for run in tc.run_results if run.evaluation == "CORRECT")
        partial_runs = sum(1 for tc in results for run in tc.run_results if run.evaluation == "PARTIAL")
        incorrect_runs = sum(1 for tc in results for run in tc.run_results if run.evaluation == "INCORRECT")
        error_runs = sum(1 for tc in results for run in tc.run_results if run.evaluation == "ERROR")
        
        success_rate = (correct_runs / total_runs * 100) if total_runs > 0 else 0
        
        all_run_times = [run.processing_time for tc in results for run in tc.run_results]
        avg_time = sum(all_run_times) / len(all_run_times) if all_run_times else 0
        
        successful_run_scores = [run.average_score for tc in results for run in tc.run_results if run.success]
        avg_score = sum(successful_run_scores) / len(successful_run_scores) if successful_run_scores else 0
        
        # Generate report
        report = f"""# LM Studio Evaluation Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Model:** gpt-oss-20b-mlx  
**Evaluation System:** LM Studio Evaluator with RAG

## Executive Summary

| Metric | Value |
|--------|-------|
| Test Cases | {total_test_cases} |
| Total Runs | {total_runs} |
| Success Rate | {success_rate:.1f}% |
| Average Score | {avg_score:.1f}/10 |
| Average Processing Time | {avg_time:.2f}s |

## Results Breakdown

| Result Type | Count | Percentage |
|-------------|-------|------------|
| ✅ Correct | {correct_runs} | {(correct_runs/total_runs*100):.1f}% |
| ⚠️ Partial | {partial_runs} | {(partial_runs/total_runs*100):.1f}% |
| ❌ Incorrect | {incorrect_runs} | {(incorrect_runs/total_runs*100):.1f}% |
| 🚫 Errors | {error_runs} | {(error_runs/total_runs*100):.1f}% |

## Test Case Analysis

"""
        
        # Add test case details
        for i, tc_result in enumerate(results, 1):
            report += f"""### Test Case {i}: {tc_result.test_case.test_id}

**Input:** {tc_result.test_case.input_text}  
**Reference:** {tc_result.test_case.reference_output}  
**Runs:** {len(tc_result.run_results)}  
**Average Score:** {tc_result.average_score_across_runs:.1f}/10  
**Best Run Score:** {tc_result.best_run_score:.1f}/10  
**Worst Run Score:** {tc_result.worst_run_score:.1f}/10  

| Run | Result | Score | Time | Timestamp |
|-----|--------|-------|------|-----------|
"""
            for run_result in tc_result.run_results:
                status = "✅" if run_result.evaluation == "CORRECT" else "⚠️" if run_result.evaluation == "PARTIAL" else "❌" if run_result.evaluation == "INCORRECT" else "🚫"
                report += f"| {run_result.test_run.run_number} | {status} {run_result.evaluation} | {run_result.average_score:.1f}/10 | {run_result.processing_time:.1f}s | {run_result.test_run.timestamp} |\n"
            
            # Add best and worst performing runs
            if tc_result.run_results:
                best_run = max(tc_result.run_results, key=lambda x: x.average_score if x.success else 0)
                worst_run = min(tc_result.run_results, key=lambda x: x.average_score if x.success else 0)
                
                report += f"""
**Best Run ({best_run.test_run.run_number}):**
- Score: {best_run.average_score:.1f}/10
- Response: {best_run.test_run.response[:200]}...
- Reasoning: {best_run.reasoning[:300]}...

**Worst Run ({worst_run.test_run.run_number}):**
- Score: {worst_run.average_score:.1f}/10  
- Response: {worst_run.test_run.response[:200]}...
- Issues: {worst_run.recommendation[:300]}...

---

"""
        
        # Add performance insights
        report += f"""## Performance Insights

### Score Distribution
"""
        
        # Calculate score distribution
        score_ranges = {"9-10": 0, "7-8": 0, "5-6": 0, "3-4": 0, "1-2": 0, "0": 0}
        for tc in results:
            for run in tc.run_results:
                if run.success:
                    score = run.average_score
                    if score >= 9: score_ranges["9-10"] += 1
                    elif score >= 7: score_ranges["7-8"] += 1
                    elif score >= 5: score_ranges["5-6"] += 1
                    elif score >= 3: score_ranges["3-4"] += 1
                    elif score >= 1: score_ranges["1-2"] += 1
                    else: score_ranges["0"] += 1
        
        for range_name, count in score_ranges.items():
            percentage = (count / successful_runs * 100) if successful_runs > 0 else 0
            report += f"- **{range_name} points:** {count} runs ({percentage:.1f}%)\n"
        
        # Add recommendations
        report += f"""
### Recommendations

"""
        if success_rate < 50:
            report += "- 🔴 **Critical:** Success rate below 50%. Review system prompts and model configuration.\n"
        elif success_rate < 70:
            report += "- 🟡 **Warning:** Success rate below 70%. Consider improving evaluation criteria.\n"
        else:
            report += "- 🟢 **Good:** Success rate above 70%. System performing well.\n"
        
        if avg_score < 6:
            report += "- 📉 **Low Scores:** Average score below 6/10. Review response quality and RAG integration.\n"
        elif avg_score < 8:
            report += "- 📊 **Moderate Scores:** Average score 6-8/10. Room for improvement in specific areas.\n"
        else:
            report += "- 📈 **High Scores:** Average score above 8/10. Excellent performance.\n"
        
        if avg_time > 5:
            report += "- ⏱️ **Performance:** Average processing time above 5s. Consider optimizing for speed.\n"
        
        # Add file information
        report += f"""
## Files Generated

- **evaluation_results.json** - Complete structured data
- **evaluation_results.csv** - Spreadsheet-ready format  
- **evaluator.log** - Detailed execution logs
- **{filename}** - This comprehensive report

---
*Report generated by LM Studio Evaluator*
"""
        
        # Write report to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Final report saved to {filename}")
        return filename
    
    def update_progressive_report(self, results: List[TestCaseResult], completed: int, total: int):
        """Update the progressive report file as test cases complete"""
        from datetime import datetime
        
        filename = "evaluation_report_progress.md"
        
        # Calculate current statistics
        total_test_cases = len(results)
        total_runs = sum(len(tc.run_results) for tc in results)
        successful_runs = sum(1 for tc in results for run in tc.run_results if run.success)
        
        correct_runs = sum(1 for tc in results for run in tc.run_results if run.evaluation == "CORRECT")
        partial_runs = sum(1 for tc in results for run in tc.run_results if run.evaluation == "PARTIAL")
        incorrect_runs = sum(1 for tc in results for run in tc.run_results if run.evaluation == "INCORRECT")
        error_runs = sum(1 for tc in results for run in tc.run_results if run.evaluation == "ERROR")
        
        success_rate = (correct_runs / total_runs * 100) if total_runs > 0 else 0
        
        all_run_times = [run.processing_time for tc in results for run in tc.run_results]
        avg_time = sum(all_run_times) / len(all_run_times) if all_run_times else 0
        
        successful_run_scores = [run.average_score for tc in results for run in tc.run_results if run.success]
        avg_score = sum(successful_run_scores) / len(successful_run_scores) if successful_run_scores else 0
        
        # Progress calculation
        progress_percent = (completed / total * 100) if total > 0 else 0
        
        # Generate progressive report
        report = f"""# LM Studio Evaluation Report - IN PROGRESS

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Model:** gpt-oss-20b-mlx  
**Evaluation System:** LM Studio Evaluator with RAG

## Progress Status

🔄 **{completed}/{total} test cases completed ({progress_percent:.1f}%)**

| Metric | Current Value |
|--------|---------------|
| Test Cases Completed | {total_test_cases}/{total} |
| Total Runs Completed | {total_runs} |
| Success Rate | {success_rate:.1f}% |
| Average Score | {avg_score:.1f}/10 |
| Average Processing Time | {avg_time:.2f}s |

## Current Results Breakdown

| Result Type | Count | Percentage |
|-------------|-------|------------|
| ✅ Correct | {correct_runs} | {(correct_runs/total_runs*100):.1f}% |
| ⚠️ Partial | {partial_runs} | {(partial_runs/total_runs*100):.1f}% |
| ❌ Incorrect | {incorrect_runs} | {(incorrect_runs/total_runs*100):.1f}% |
| 🚫 Errors | {error_runs} | {(error_runs/total_runs*100):.1f}% |

## Completed Test Cases

"""
        
        # Add completed test case details with reasoning
        for i, tc_result in enumerate(results, 1):
            report += f"""### ✅ Test Case {i}: {tc_result.test_case.test_id}

**Input:** {tc_result.test_case.input_text[:100]}...  
**Reference:** {tc_result.test_case.reference_output[:100]}...  
**Average Score:** {tc_result.average_score_across_runs:.1f}/10  
**Runs:** {len(tc_result.run_results)}

| Run | Result | Score | Time |
|-----|--------|-------|------|
"""
            for run_result in tc_result.run_results:
                status = "✅" if run_result.evaluation == "CORRECT" else "⚠️" if run_result.evaluation == "PARTIAL" else "❌" if run_result.evaluation == "INCORRECT" else "🚫"
                report += f"| {run_result.test_run.run_number} | {status} {run_result.evaluation} | {run_result.average_score:.1f}/10 | {run_result.processing_time:.1f}s |\n"
            
            # Add detailed analysis for each run
            for run_result in tc_result.run_results:
                status_emoji = "✅" if run_result.evaluation == "CORRECT" else "⚠️" if run_result.evaluation == "PARTIAL" else "❌" if run_result.evaluation == "INCORRECT" else "🚫"
                
                report += f"""
#### {status_emoji} Run {run_result.test_run.run_number} - {run_result.evaluation}

**Response:** {run_result.test_run.response[:200]}...

**Detailed Scores:**
- Factual Accuracy: {run_result.detailed_scores.factual_accuracy}/10
- Completeness: {run_result.detailed_scores.completeness}/10
- Order/Sequence: {run_result.detailed_scores.order_sequence}/10
- Relevance: {run_result.detailed_scores.relevance}/10
- Overall Quality: {run_result.detailed_scores.overall_quality}/10

**RAG Verification:**
{run_result.rag_verification[:300]}...

**Reasoning:**
{run_result.reasoning[:400]}...

**Recommendation:**
{run_result.recommendation[:200]}...

"""
            
            report += "\n---\n\n"
        
        # Add remaining test cases info
        if completed < total:
            remaining = total - completed
            report += f"""## Remaining Test Cases

⏳ **{remaining} test cases remaining**

The evaluation will continue automatically. This report updates after each test case completion.

---
*Progressive report - updates in real-time*
"""
        else:
            report += """## Evaluation Complete! ✅

All test cases have been processed. Check the final report for complete analysis.

---
*Evaluation finished - see evaluation_report.md for final comprehensive report*
"""
        
        # Write progressive report to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Progressive report updated: {completed}/{total} test cases completed")

def main():
    """Main function to run the evaluator"""
    try:
        # Initialize evaluator
        evaluator = LMStudioEvaluator()
        
        # Parse test cases from user data file
        test_cases = evaluator.parse_user_test_data()
        
        if not test_cases:
            logger.error("No test cases found in user_test_data.txt")
            sys.exit(1)
        
        logger.info(f"Loaded {len(test_cases)} test cases")
        
        # Run evaluation
        results = evaluator.evaluate_batch(test_cases)
        
        # Print results
        evaluator.print_results_summary(results)
        
        # Save results to file
        results_data = []
        for tc_result in results:
            for run_result in tc_result.run_results:
                result_dict = {
                    "test_id": tc_result.test_case.test_id,
                    "run_number": run_result.test_run.run_number,
                    "timestamp": run_result.test_run.timestamp,
                    "input": tc_result.test_case.input_text,
                    "reference_output": tc_result.test_case.reference_output,
                    "actual_output": run_result.test_run.response,
                    "evaluation": run_result.evaluation,
                    "processing_time": run_result.processing_time,
                    "success": run_result.success,
                    "average_score": run_result.average_score if run_result.success else 0
                }
                
                # Add detailed scores if available
                if run_result.success and run_result.detailed_scores:
                    result_dict.update({
                        "detailed_scores": {
                            "factual_accuracy": run_result.detailed_scores.factual_accuracy,
                            "completeness": run_result.detailed_scores.completeness,
                            "order_sequence": run_result.detailed_scores.order_sequence,
                            "relevance": run_result.detailed_scores.relevance,
                            "overall_quality": run_result.detailed_scores.overall_quality
                        },
                        "rag_verification": run_result.rag_verification,
                        "reasoning": run_result.reasoning,
                        "recommendation": run_result.recommendation
                    })
                
                results_data.append(result_dict)
        
        with open("evaluation_results.json", "w") as f:
            json.dump(results_data, f, indent=2)
        
        # Export to CSV for easy analysis
        evaluator.export_results_to_csv(results)
        
        # Generate comprehensive final report
        report_file = evaluator.generate_final_report(results)
        
        logger.info(f"Multi-run results saved to evaluation_results.json, evaluation_results.csv, and {report_file}")
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
