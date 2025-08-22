#!/usr/bin/env python3
"""
Test script to verify LM Studio tools and RAG implementation
"""

import json
from openai import OpenAI

def test_basic_call():
    """Test basic API call without tools"""
    client = OpenAI(
        base_url="http://127.0.0.1:1234/v1",
        api_key="not-needed"
    )
    
    print("🧪 Testing basic API call...")
    try:
        response = client.chat.completions.create(
            model="gpt-oss-20b-mlx",
            messages=[
                {"role": "user", "content": "What is 2+2?"}
            ]
        )
        print("✅ Basic call successful")
        print(f"Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ Basic call failed: {e}")
        return False

def test_tools_call():
    """Test API call with tools parameter"""
    client = OpenAI(
        base_url="http://127.0.0.1:1234/v1",
        api_key="not-needed"
    )
    
    print("\n🔧 Testing tools parameter...")
    try:
        response = client.chat.completions.create(
            model="gpt-oss-20b-mlx",
            messages=[
                {"role": "user", "content": "Search for information about the speed of light"}
            ],
            tools=[
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
            ],
            tool_choice="auto"
        )
        print("✅ Tools call successful")
        print(f"Response: {response.choices[0].message.content}")
        
        # Check if model made tool calls
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            print("🎯 Model made tool calls!")
            for tool_call in response.choices[0].message.tool_calls:
                print(f"Tool called: {tool_call.function.name}")
                print(f"Arguments: {tool_call.function.arguments}")
        else:
            print("ℹ️ No tool calls made (normal response)")
        
        return True
    except Exception as e:
        print(f"❌ Tools call failed: {e}")
        return False

def test_rag_query():
    """Test RAG-style query"""
    client = OpenAI(
        base_url="http://127.0.0.1:1234/v1",
        api_key="not-needed"
    )
    
    print("\n📚 Testing RAG query...")
    try:
        response = client.chat.completions.create(
            model="gpt-oss-20b-mlx",
            messages=[
                {"role": "system", "content": "You have access to a knowledge base. Use it to provide accurate information."},
                {"role": "user", "content": "According to the knowledge base, what is the exact speed of light in vacuum?"}
            ]
        )
        print("✅ RAG query successful")
        print(f"Response: {response.choices[0].message.content}")
        
        # Check if response seems to reference knowledge base
        response_text = response.choices[0].message.content.lower()
        if any(phrase in response_text for phrase in ["knowledge base", "according to", "299,792,458"]):
            print("🎯 Response seems to reference knowledge base!")
        else:
            print("ℹ️ Response doesn't explicitly reference knowledge base")
        
        return True
    except Exception as e:
        print(f"❌ RAG query failed: {e}")
        return False

def test_evaluation_style():
    """Test evaluation-style call with system prompt"""
    client = OpenAI(
        base_url="http://127.0.0.1:1234/v1",
        api_key="not-needed"
    )
    
    print("\n⚖️ Testing evaluation-style call...")
    
    system_prompt = """You are an expert evaluation assistant with access to a knowledge base through RAG. 
Evaluate the following response for accuracy using your knowledge base.

Respond in this format:
EVALUATION_RESULT: [CORRECT|INCORRECT|PARTIAL]
REASONING: [explanation]"""
    
    evaluation_request = """Now evaluate the following:
Input: What is the speed of light?
Expected Output: 299,792,458 meters per second
Actual Output: The speed of light is approximately 300,000 km/s

Begin evaluation:"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-oss-20b-mlx",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": evaluation_request}
            ],
            temperature=0.1
        )
        print("✅ Evaluation call successful")
        print(f"Response: {response.choices[0].message.content}")
        
        # Check if response follows expected format
        response_text = response.choices[0].message.content
        if "EVALUATION_RESULT:" in response_text and "REASONING:" in response_text:
            print("🎯 Response follows evaluation format!")
        else:
            print("ℹ️ Response doesn't follow expected evaluation format")
        
        return True
    except Exception as e:
        print(f"❌ Evaluation call failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 LM Studio Tools and RAG Test Suite")
    print("=" * 50)
    
    tests = [
        ("Basic API Call", test_basic_call),
        ("Tools Parameter", test_tools_call),
        ("RAG Query", test_rag_query),
        ("Evaluation Style", test_evaluation_style)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        if test_func():
            passed += 1
    
    print(f"\n{'='*50}")
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! LM Studio integration is working correctly.")
        print("💡 You can now run the evaluator with confidence.")
    else:
        print("⚠️ Some tests failed. Check LM Studio server status and configuration.")
        print("💡 Common fixes:")
        print("   - Ensure LM Studio server is running")
        print("   - Check that gpt-oss-20b-mlx model is loaded")
        print("   - Verify RAG/documents are properly configured")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
