#!/usr/bin/env python3
"""
RAG-v1 Plugin Integration Test
Tests the RAG-v1 plugin functionality with file upload and citation retrieval
"""

import json
import os
from openai import OpenAI

def test_rag_v1_plugin():
    """Test RAG-v1 plugin integration with file uploads"""
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    client = OpenAI(
        base_url=config["lm_studio"]["base_url"],
        api_key=config["lm_studio"]["api_key"]
    )
    
    print("🚀 Testing RAG-v1 Plugin Integration")
    print("=" * 60)
    
    # Test messages that should trigger RAG-v1 citation retrieval
    test_scenarios = [
        {
            "name": "Offer ID Verification",
            "system": """You are an evaluation assistant with access to a knowledge base through RAG-v1 plugin.
When evaluating, use citations provided by the plugin to verify offer information.""",
            "user": "I need to verify if offer ID 61 exists and if it has Indulge=true. Please search the knowledge base.",
            "expected_citations": True
        },
        {
            "name": "Category Search",
            "system": "You have access to offer information through citations. Use them to answer questions.",
            "user": "List all restaurant offers that have Indulge=true attribute.",
            "expected_citations": True
        },
        {
            "name": "Evaluation Context",
            "system": config.get("system_prompt", "You are an evaluation assistant."),
            "user": """Evaluate this LLM response:
Input: "Show me Indulge offers"
Expected: "Return only offers with Indulge=true"
Actual: {"offers": [{"id": "61"}, {"id": "66"}], "text": "Here are your Indulge offers"}

Please verify if offer IDs 61 and 66 are actually marked as Indulge=true.""",
            "expected_citations": True
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print("-" * 40)
        print(f"System: {scenario['system'][:100]}...")
        print(f"User: {scenario['user'][:100]}...")
        print()
        
        try:
            # Note: For RAG-v1 to work, knowledge_base.txt should be uploaded to LM Studio
            # The plugin will automatically retrieve relevant citations
            response = client.chat.completions.create(
                model=config["lm_studio"]["model_name"],
                messages=[
                    {"role": "system", "content": scenario['system']},
                    {"role": "user", "content": scenario['user']}
                ],
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            print(f"Response: {content}")
            print()
            
            # Check for citation indicators from RAG-v1
            citation_indicators = [
                "Citation 1:", "Citation 2:", "Citation 3:",
                "citations were found", "relevant citations",
                "According to", "Based on the citations"
            ]
            
            has_citations = any(indicator in content for indicator in citation_indicators)
            
            if has_citations:
                print("✅ RAG-v1 citations detected!")
                # Extract and display citations if found
                lines = content.split('\n')
                for line in lines:
                    if 'Citation' in line and ':' in line:
                        print(f"📄 {line.strip()}")
            else:
                print("⚠️ No RAG-v1 citations detected")
                if scenario['expected_citations']:
                    print("   Expected citations but none found - check RAG-v1 setup")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n" + "="*60)

def setup_instructions():
    """Print setup instructions for RAG-v1"""
    print("\n💡 RAG-v1 Setup Instructions:")
    print("=" * 60)
    print("1. Ensure RAG-v1 plugin is installed in LM Studio")
    print("2. In LM Studio, go to Chat interface")
    print("3. Upload knowledge_base.txt file using document upload")
    print("4. Configure RAG-v1 plugin settings:")
    print("   - Retrieval Limit: 5")
    print("   - Retrieval Affinity Threshold: 0.6")
    print("5. Test with: 'What offers have Indulge=true?'")
    print("6. You should see 'Citation 1:', 'Citation 2:' in responses")
    print("\n📋 Expected RAG-v1 Response Format:")
    print("The following citations were found in the files provided by the user:")
    print("")
    print("Citation 1: \"Offer ID: 61, Category: restaurant, Indulge: true\"")
    print("Citation 2: \"Offer ID: 66, Category: hotel, Indulge: true\"")
    print("")
    print("Based on the citations above, offers 61 and 66 have Indulge=true...")

if __name__ == "__main__":
    test_rag_v1_plugin()
    setup_instructions()
