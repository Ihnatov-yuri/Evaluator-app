#!/usr/bin/env python3
"""
Direct RAG Test Script
Tests if LM Studio RAG/tools functionality is working properly
"""

import json
from openai import OpenAI

def test_rag_directly():
    """Test RAG functionality directly with LM Studio"""
    
    # Load config
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    # Initialize client
    client = OpenAI(
        base_url=config["lm_studio"]["base_url"],
        api_key=config["lm_studio"]["api_key"]
    )
    
    # Test message with tools
    messages = [
        {
            "role": "system", 
            "content": "You have access to a knowledge base via the search_knowledge_base function. Use it to answer questions about offers."
        },
        {
            "role": "user", 
            "content": "What offer IDs are marked as Indulge=true in your knowledge base? Use the search_knowledge_base function to find this information."
        }
    ]
    
    # Define tools for RAG
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_knowledge_base",
                "description": "Search the knowledge base for information about offers, IDs, and other factual data",
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
    
    print("🔍 Testing RAG functionality with LM Studio...")
    print(f"Server: {config['lm_studio']['base_url']}")
    print(f"Model: {config['lm_studio']['model_name']}")
    print()
    
    try:
        # Test with tools
        print("📡 Sending request with RAG tools...")
        response = client.chat.completions.create(
            model=config["lm_studio"]["model_name"],
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.1
        )
        
        print("✅ Response received!")
        print("📝 Content:")
        print(response.choices[0].message.content)
        print()
        
        # Check if tools were used
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            print("🛠️ Tools were called:")
            for tool_call in response.choices[0].message.tool_calls:
                print(f"  - Function: {tool_call.function.name}")
                print(f"  - Arguments: {tool_call.function.arguments}")
        else:
            print("⚠️ No tools were called - RAG may not be working properly!")
        
    except Exception as e:
        print(f"❌ Error testing RAG: {e}")
        print()
        print("🔧 Possible issues:")
        print("1. LM Studio server not running")
        print("2. RAG/tools not enabled in LM Studio")
        print("3. Knowledge base not indexed")
        print("4. Model doesn't support function calling")

def test_without_tools():
    """Test basic connection without tools"""
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    client = OpenAI(
        base_url=config["lm_studio"]["base_url"],
        api_key=config["lm_studio"]["api_key"]
    )
    
    print("🧪 Testing basic connection (no tools)...")
    
    try:
        response = client.chat.completions.create(
            model=config["lm_studio"]["model_name"],
            messages=[
                {"role": "user", "content": "Hello, can you access any knowledge base or documents?"}
            ],
            temperature=0.1
        )
        
        print("✅ Basic connection works!")
        print("📝 Response:")
        print(response.choices[0].message.content)
        print()
        
    except Exception as e:
        print(f"❌ Basic connection failed: {e}")

if __name__ == "__main__":
    print("🚀 LM Studio RAG Test Suite")
    print("=" * 50)
    
    # Test basic connection first
    test_without_tools()
    print("-" * 50)
    
    # Test RAG functionality
    test_rag_directly()
    
    print("\n💡 Next steps if RAG isn't working:")
    print("1. Open LM Studio")
    print("2. Go to Chat tab")
    print("3. Upload knowledge_base.txt file")
    print("4. Wait for indexing to complete")
    print("5. Test with: 'What offers are marked Indulge=true?'")
