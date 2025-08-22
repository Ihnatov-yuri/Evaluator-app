#!/usr/bin/env python3
"""
Quick RAG status test
"""

import json
from openai import OpenAI

def test_rag_status():
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    client = OpenAI(
        base_url=config["lm_studio"]["base_url"],
        api_key=config["lm_studio"]["api_key"]
    )
    
    print("🔍 Testing RAG Status...")
    
    # Simple test with tools to see if they're called
    try:
        response = client.chat.completions.create(
            model=config["lm_studio"]["model_name"],
            messages=[
                {"role": "user", "content": "What is OfferId 1? Use your knowledge base to find this offer."}
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "search_knowledge_base",
                        "description": "Search knowledge base",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query"}
                            },
                            "required": ["query"]
                        }
                    }
                }
            ],
            tool_choice="auto",
            temperature=0.1
        )
        
        content = response.choices[0].message.content
        print(f"Response: {content}")
        
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            print("✅ Tool calls detected!")
            for tool_call in response.choices[0].message.tool_calls:
                print(f"Function: {tool_call.function.name}")
                print(f"Arguments: {tool_call.function.arguments}")
        else:
            print("❌ No tool calls - RAG not working")
            
        if "Citation" in content:
            print("✅ Citations found in response!")
        else:
            print("❌ No citations - knowledge base not accessed")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_rag_status()
