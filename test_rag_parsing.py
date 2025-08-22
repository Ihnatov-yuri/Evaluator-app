#!/usr/bin/env python3
"""
Test RAG parsing strategy in LM Studio
Tests different types of queries to see how well the knowledge base is indexed
"""

import json
from openai import OpenAI

def test_rag_parsing():
    """Test different types of RAG queries"""
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    client = OpenAI(
        base_url=config["lm_studio"]["base_url"],
        api_key=config["lm_studio"]["api_key"]
    )
    
    # Test queries for different parsing strategies
    test_queries = [
        {
            "name": "Exact ID Search",
            "query": "What is offer ID 61? Is it marked as Indulge=true?",
            "expected": "Should find exact offer information"
        },
        {
            "name": "Category Search", 
            "query": "List all restaurant offers with Indulge=true",
            "expected": "Should find category-based results"
        },
        {
            "name": "Location Search",
            "query": "What offers are available in downtown area?",
            "expected": "Should find location-based results"
        },
        {
            "name": "Attribute Search",
            "query": "Which offers have the attribute Indulge=true?",
            "expected": "Should find attribute-based matches"
        }
    ]
    
    print("🔍 Testing RAG Parsing Strategy")
    print("=" * 60)
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{i}. {test['name']}")
        print(f"Query: {test['query']}")
        print(f"Expected: {test['expected']}")
        print("-" * 40)
        
        try:
            response = client.chat.completions.create(
                model=config["lm_studio"]["model_name"],
                messages=[
                    {
                        "role": "system",
                        "content": "You have access to a knowledge base about offers. Search thoroughly and provide specific information."
                    },
                    {
                        "role": "user", 
                        "content": test['query']
                    }
                ],
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            print(f"Response: {content}")
            
            # Check if response indicates knowledge base access
            if any(phrase in content.lower() for phrase in [
                "according to", "found in", "knowledge base", "document", 
                "offer id", "indulge=true", "specific offer"
            ]):
                print("✅ Appears to access knowledge base")
            else:
                print("⚠️ May not be accessing knowledge base properly")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()

if __name__ == "__main__":
    test_rag_parsing()
    
    print("\n💡 RAG Optimization Tips:")
    print("1. In LM Studio, try different chunk sizes (512, 1024, 2048)")
    print("2. Adjust similarity threshold for retrieval")
    print("3. Use structured data format in knowledge base")
    print("4. Test with exact ID queries vs semantic queries")
    print("5. Check document preprocessing settings")
