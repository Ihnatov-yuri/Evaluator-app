#!/usr/bin/env python3
"""
Setup Test Script

This script validates that all components are properly configured
and LM Studio server is accessible.
"""

import json
import sys
from pathlib import Path
import requests
from evaluator import LMStudioEvaluator, TestCase, TestRun

def test_file_existence():
    """Test that all required files exist"""
    required_files = [
        "config.json",
        "evaluation_prompt.txt",
        "evaluator.py",
        "requirements.txt"
    ]
    
    print("🔍 Checking required files...")
    missing_files = []
    
    for file_name in required_files:
        if not Path(file_name).exists():
            missing_files.append(file_name)
        else:
            print(f"  ✅ {file_name}")
    
    if missing_files:
        print(f"  ❌ Missing files: {missing_files}")
        return False
    
    print("  ✅ All required files present")
    return True

def test_config_validity():
    """Test that configuration is valid"""
    print("\n🔍 Checking configuration...")
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        
        required_keys = [
            "lm_studio", "model_parameters", "evaluation", "rag"
        ]
        
        for key in required_keys:
            if key not in config:
                print(f"  ❌ Missing config section: {key}")
                return False
            else:
                print(f"  ✅ {key} section present")
        
        print("  ✅ Configuration is valid")
        return True
        
    except json.JSONDecodeError as e:
        print(f"  ❌ Invalid JSON in config.json: {e}")
        return False
    except FileNotFoundError:
        print("  ❌ config.json not found")
        return False

def test_server_connection():
    """Test connection to LM Studio server"""
    print("\n🔍 Testing LM Studio server connection...")
    
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        
        base_url = config["lm_studio"]["base_url"].replace("/v1", "")
        
        # Test health endpoint
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                print("  ✅ Server is responding")
            else:
                print(f"  ⚠️  Server responded with status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Cannot connect to server: {e}")
            print(f"  💡 Make sure LM Studio is running at {base_url}")
            return False
        
        # Test models endpoint
        try:
            response = requests.get(f"{config['lm_studio']['base_url']}/models", timeout=5)
            if response.status_code == 200:
                models = response.json()
                model_names = [m.get("id", "") for m in models.get("data", [])]
                print(f"  ✅ Available models: {model_names}")
                
                target_model = config["lm_studio"]["model_name"]
                if target_model in model_names:
                    print(f"  ✅ Target model '{target_model}' is available")
                else:
                    print(f"  ⚠️  Target model '{target_model}' not found in available models")
                    print(f"  💡 Load the model in LM Studio or update config.json")
                    return False
            else:
                print(f"  ⚠️  Models endpoint returned status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  Cannot check models: {e}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error testing server: {e}")
        return False

def test_evaluator_initialization():
    """Test evaluator initialization"""
    print("\n🔍 Testing evaluator initialization...")
    
    try:
        evaluator = LMStudioEvaluator()
        print("  ✅ Evaluator initialized successfully")
        
        # Test prompt loading
        if evaluator.prompt_template:
            print("  ✅ Evaluation prompt loaded")
        else:
            print("  ❌ Evaluation prompt not loaded")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to initialize evaluator: {e}")
        return False

def test_simple_evaluation():
    """Run a simple test evaluation"""
    print("\n🔍 Running simple test evaluation...")
    
    try:
        evaluator = LMStudioEvaluator()
        
        # Simple test case with run
        test_run = TestRun(
            run_number=1,
            timestamp="2025-08-22 - 14:45:00",
            response="2"
        )
        
        test_case = TestCase(
            test_id="simple_test",
            input_text="What is 1 + 1?",
            reference_output="2",
            runs=[test_run]
        )
        
        print("  🚀 Running test case...")
        result = evaluator.evaluate_single_run(test_case, test_run)
        
        if result.success:
            print(f"  ✅ Test completed: {result.evaluation}")
            print(f"  📊 Processing time: {result.processing_time:.2f}s")
            print(f"  📝 Response: {result.test_run.response}")
            return True
        else:
            print(f"  ❌ Test failed: {result.reasoning}")
            return False
            
    except Exception as e:
        print(f"  ❌ Test evaluation failed: {e}")
        return False

def main():
    """Run all tests"""
    print("LM Studio Evaluator - Setup Test")
    print("=" * 50)
    
    tests = [
        ("File Existence", test_file_existence),
        ("Configuration", test_config_validity),
        ("Server Connection", test_server_connection),
        ("Evaluator Initialization", test_evaluator_initialization),
        ("Simple Evaluation", test_simple_evaluation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"\n❌ {test_name} test failed")
        except Exception as e:
            print(f"\n❌ {test_name} test failed with exception: {e}")
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The evaluator is ready to use.")
        print("💡 Run 'python example_usage.py' to start evaluating your test cases.")
    else:
        print("❌ Some tests failed. Please check the issues above.")
        print("💡 Common fixes:")
        print("   - Start LM Studio server")
        print("   - Load gpt-oss-20b-mlx model")
        print("   - Check network connectivity")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
