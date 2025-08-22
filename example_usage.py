#!/usr/bin/env python3
"""
Example usage of the LM Studio Evaluator

This script demonstrates how to use the evaluator with custom test cases.
Modify the test_cases list to include your specific inputs and expected outputs.
"""

from evaluator import LMStudioEvaluator, TestCase, TestRun

def main():
    """
    Main function to run evaluations using the user_test_data.txt file
    """
    print("LM Studio Evaluator - Multi-Run Analysis")
    print("=" * 50)
    
    try:
        # Initialize the evaluator
        evaluator = LMStudioEvaluator()
        
        # Parse test cases from the user data file
        print("Loading test cases from user_test_data.txt...")
        test_cases = evaluator.parse_user_test_data()
        
        if not test_cases:
            print("❌ No test cases found in user_test_data.txt")
            return
        
        total_runs = sum(len(tc.runs) for tc in test_cases)
        print(f"📋 Loaded {len(test_cases)} test cases with {total_runs} total runs")
        print("Starting evaluation...\n")
        
        # Run the evaluation
        results = evaluator.evaluate_batch(test_cases)
        
        # Display results
        evaluator.print_results_summary(results)
        
        # Export to CSV for spreadsheet analysis
        evaluator.export_results_to_csv(results)
        
        # Generate comprehensive final report
        report_file = evaluator.generate_final_report(results)
        
        print("\nEvaluation completed successfully!")
        print("📄 Check 'evaluation_results.json' for detailed JSON results.")
        print("📊 Check 'evaluation_results.csv' for spreadsheet analysis.")
        print(f"📋 Check '{report_file}' for comprehensive markdown report.")
        print("📝 Check 'evaluator.log' for detailed logs.")
        
    except Exception as e:
        print(f"Error during evaluation: {e}")
        print("Please check:")
        print("1. LM Studio server is running at http://127.0.0.1:1234")
        print("2. gpt-oss-20b-mlx model is loaded")
        print("3. user_test_data.txt file exists and is properly formatted")
        print("4. All required files are present")

if __name__ == "__main__":
    main()
