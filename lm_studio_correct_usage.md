# LM Studio Tools and RAG - Correct Implementation Guide

Based on official LM Studio documentation, here's how to properly implement tools and RAG.

## 🔧 **Tools Implementation**

### 1. Tools Parameter Structure
LM Studio uses the `tools` parameter in `/v1/chat/completions` requests:

```json
{
  "model": "gpt-oss-20b-mlx",
  "messages": [...],
  "tools": [
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
  "tool_choice": "auto"
}
```

### 2. General Usage Flow
1. **Send tools list** with API request
2. **Parse model's tool_calls** response  
3. **Execute matching function** with provided arguments
4. **Return results to model**

### 3. Model Response Handling
The model can either:
- **Call a tool**: `<tool_call>{"name": "search_knowledge_base", "arguments": {"query": "speed of light"}}</tool_call>`
- **Respond normally**: Regular text response

## 📚 **RAG Implementation**

### Method 1: Document Attachment (Recommended)
1. **Attach documents** to LM Studio chat session:
   - Drag and drop `.txt`, `.pdf`, `.docx` files
   - LM Studio automatically handles RAG

2. **Document Processing**:
   - **Short docs**: Entire content added to context
   - **Long docs**: RAG retrieval of relevant portions

3. **Effective Querying**:
   - Include specific terms from your documents
   - Provide context in queries
   - Reference document content explicitly

### Method 2: Tools-based RAG
Use tools parameter to define knowledge base search functions (as implemented in our evaluator).

## 🏗️ **Our Implementation Structure**

### File Organization
```
/Users/yuri/Documents/Evaluator app/
├── system_prompt.txt          # System message for evaluation
├── user_test_data.txt         # Test cases and user data  
├── knowledge_base.txt         # RAG knowledge base
├── evaluator.py              # Main evaluator with tools
└── config.json               # Configuration
```

### Configuration (config.json)
```json
{
  "rag": {
    "enabled": true,
    "use_tools": true,
    "search_depth": "medium"
  }
}
```

### System Prompt Integration
The `system_prompt.txt` contains evaluation instructions that reference RAG:
```
Use your RAG knowledge base to verify all factual claims...
MANDATORY RAG VERIFICATION:
- Use your knowledge base to fact-check every claim...
```

## 🚀 **LM Studio Setup for RAG**

### Option A: Document Attachment
1. Open LM Studio chat interface
2. Drag `knowledge_base.txt` into chat
3. Start conversation - RAG is automatic

### Option B: Server-side RAG
1. **Configure LM Studio Server**:
   - Go to Local Server tab
   - Load `gpt-oss-20b-mlx` model
   - Enable document/RAG features
   - Point to folder with `knowledge_base.txt`

2. **Start Server** with RAG enabled at `http://127.0.0.1:1234`

### Option C: Tools-based (Our Implementation)
Our evaluator sends tools parameter to enable knowledge base search.

## 🧪 **Testing RAG Integration**

### 1. Test Basic RAG
```bash
curl -X POST http://127.0.0.1:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-20b-mlx",
    "messages": [
      {"role": "user", "content": "According to the knowledge base, what is the speed of light?"}
    ]
  }'
```

### 2. Test Tools Integration
```bash
curl -X POST http://127.0.0.1:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-20b-mlx",
    "messages": [
      {"role": "user", "content": "Search for information about photosynthesis"}
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "search_knowledge_base",
          "description": "Search knowledge base",
          "parameters": {
            "type": "object",
            "properties": {
              "query": {"type": "string"}
            }
          }
        }
      }
    ],
    "tool_choice": "auto"
  }'
```

## 🔍 **Evaluation Workflow**

### 1. Question Processing
- Input from `user_test_data.txt`
- System prompt from `system_prompt.txt`

### 2. RAG-Enhanced Response
- Model uses tools to search `knowledge_base.txt`
- Generates response with verified facts

### 3. Evaluation Phase
- System prompt guides evaluation criteria
- RAG verification against knowledge base
- Structured scoring output

## 🐛 **Troubleshooting**

### Tools Not Working
```
Error: "Expected array, received string"
```
**Solution**: Ensure `tools` parameter is properly formatted array

### RAG Not Responding
**Check**:
1. Document is attached/loaded
2. Query includes relevant keywords
3. LM Studio server RAG is enabled
4. Knowledge base file is accessible

### Model Not Using Tools
**Check**:
1. `tool_choice` is set to "auto"
2. Tool descriptions are clear
3. Model supports function calling
4. Tool parameters are valid JSON schema

## 📈 **Performance Tips**

### RAG Optimization
1. **Keep knowledge base focused** - relevant facts only
2. **Use clear headings** in knowledge base
3. **Structure data logically** - group related facts
4. **Test with simple queries** first

### Tools Optimization
1. **Clear function descriptions** - help model understand usage
2. **Simple parameter schemas** - avoid complex nested objects
3. **Descriptive parameter names** - make purpose obvious
4. **Required fields only** - minimize complexity

This implementation follows LM Studio's official documentation and provides robust RAG evaluation capabilities.
