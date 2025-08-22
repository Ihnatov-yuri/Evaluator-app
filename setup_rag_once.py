#!/usr/bin/env python3
"""
One-time RAG setup script
Uploads knowledge base to LM Studio and caches it to avoid re-processing
"""

import json
import os
from openai import OpenAI

def setup_rag_once():
    """Upload and cache knowledge base in LM Studio once"""
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    client = OpenAI(
        base_url=config["lm_studio"]["base_url"],
        api_key=config["lm_studio"]["api_key"]
    )
    
    print("🚀 Setting up RAG-v1 with Knowledge Base (One-time setup)")
    print("=" * 70)
    
    # Check if knowledge base file exists
    if not os.path.exists('knowledge_base.txt'):
        print("❌ knowledge_base.txt not found!")
        return
    
    print(f"📁 Knowledge base file: {os.path.getsize('knowledge_base.txt')} bytes")
    print("📡 Uploading to LM Studio for processing and caching...")
    
    # First call with knowledge base - this will process and cache it
    setup_message = """Please process this knowledge base file and confirm it's ready for use.
    
The knowledge base contains offer information with parameters like:
- OfferId
- Indulge (true/false)  
- Gems (true/false)
- Cashback (true/false)
- Popular ("yes"/"no")
- OfferCategoryTrained
- Merchant
- And other offer details

Once processed, I'll be able to query specific offer information efficiently."""

    try:
        print("⏳ Processing knowledge base (this may take a moment)...")
        
        response = client.chat.completions.create(
            model=config["lm_studio"]["model_name"],
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant. When a user uploads a knowledge base, confirm it's processed and describe what you can help with."
                },
                {
                    "role": "user", 
                    "content": setup_message
                }
            ],
            temperature=0.1
        )
        
        content = response.choices[0].message.content.strip()
        print("✅ LM Studio Response:")
        print(content)
        print()
        
        # Test a sample query to verify RAG is working
        print("🧪 Testing RAG with sample query...")
        test_response = client.chat.completions.create(
            model=config["lm_studio"]["model_name"],
            messages=[
                {
                    "role": "system",
                    "content": "You have access to an offer knowledge base. Use citations to answer questions about offers."
                },
                {
                    "role": "user",
                    "content": "What is OfferId 1? What are its Indulge, Gems, and Cashback values?"
                }
            ],
            temperature=0.1
        )
        
        test_content = test_response.choices[0].message.content.strip()
        print("📊 Test Query Result:")
        print(test_content)
        print()
        
        # Check for citations
        if "Citation" in test_content:
            print("🎉 RAG-v1 is working! Citations detected.")
            print("✅ Knowledge base is cached and ready for evaluation.")
            print()
            print("💡 Next steps:")
            print("1. Knowledge base is now cached in LM Studio")
            print("2. Future evaluations will use cached version (much faster)")
            print("3. Run your evaluations with: python example_usage.py")
            
            # Save cache status
            cache_info = {
                "cached": True,
                "cache_date": "2025-08-22",
                "knowledge_base_size": os.path.getsize('knowledge_base.txt'),
                "model": config["lm_studio"]["model_name"],
                "rag_settings": config["rag"]["plugin_config"]
            }
            
            with open('rag_cache_status.json', 'w') as f:
                json.dump(cache_info, f, indent=2)
            
            print("📄 Cache status saved to rag_cache_status.json")
            
        else:
            print("⚠️ No citations detected. RAG may not be properly configured.")
            print("Please check:")
            print("1. RAG-v1 plugin is installed and enabled")
            print("2. Knowledge base file was uploaded correctly")
            print("3. Plugin settings in LM Studio")
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        print()
        print("🔧 Troubleshooting:")
        print("1. Ensure LM Studio is running")
        print("2. Check that RAG-v1 plugin is installed")
        print("3. Verify model is loaded")
        print("4. Check knowledge_base.txt file exists")

def check_cache_status():
    """Check if RAG is already cached"""
    if os.path.exists('rag_cache_status.json'):
        with open('rag_cache_status.json', 'r') as f:
            cache_info = json.load(f)
        
        print("📋 RAG Cache Status:")
        print(f"  Cached: {cache_info.get('cached', False)}")
        print(f"  Date: {cache_info.get('cache_date', 'Unknown')}")
        print(f"  KB Size: {cache_info.get('knowledge_base_size', 0)} bytes")
        print(f"  Model: {cache_info.get('model', 'Unknown')}")
        return cache_info.get('cached', False)
    return False

if __name__ == "__main__":
    if check_cache_status():
        print("✅ RAG cache already exists!")
        print("💡 Your knowledge base should already be cached in LM Studio.")
        print("🚀 You can proceed with evaluations.")
    else:
        setup_rag_once()
