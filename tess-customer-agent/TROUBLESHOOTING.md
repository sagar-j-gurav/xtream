# TESS Troubleshooting Guide

## Common Issues and Solutions

### 1. OpenAI API Quota Exceeded Error

**Error Message:**
```
Error code: 429 - You exceeded your current quota, please check your plan and billing details
```

**Cause:** Your OpenAI account has run out of credits or exceeded its rate limit.

**Solutions:**

1. **Add Credits to OpenAI Account:**
   - Go to: https://platform.openai.com/account/billing
   - Add payment method and purchase credits
   - Minimum $5 recommended for testing

2. **Check Your Usage:**
   - View usage: https://platform.openai.com/usage
   - Check if you've exceeded your plan limits

3. **Check Your API Key:**
   - Verify key is correct in `.env.dev`
   - Ensure key has proper permissions

**Expected Costs for TESS:**
- **Embeddings** (text-embedding-3-small): ~$0.02 per 1M tokens
  - 565 FAQs (~200 words each) ≈ 113K tokens ≈ **$0.002**
- **Chat completions** (gpt-4o-mini): $0.150 per 1M input tokens
  - 100 conversations ≈ **$0.01-0.05**

**Total estimated cost for initial testing: <$1**

---

### 2. Agent Responding with Generic Greeting Instead of Using Tools

**Symptoms:**
- Agent says "Hi there! I'm TESS..." for every query
- Logs show tools are loaded and called
- But final response doesn't use tool results

**Debugging Steps:**

1. **Check if tools are loaded:**
   ```bash
   # Look for this in logs
   grep "Total tools available" logs/tess.log
   # Should show: Total tools available: 4
   ```

2. **Check if tool is being called:**
   ```bash
   # Look for tool execution
   grep "Routing to tools" logs/tess.log
   ```

3. **Check tool results:**
   ```bash
   # Enable debug logging in .env.dev
   LOG_LEVEL=DEBUG
   ```

4. **Test each tool individually** via API docs:
   - Go to: http://0.0.0.0:8000/docs
   - Test `/api/v1/chat` endpoint with different queries

**Common Causes:**

- **Empty knowledge base**: If no FAQs uploaded, search_knowledge_base returns no results
- **MCP tool errors**: Frappe MCP server might be returning errors
- **Conversation history**: Previous messages might be confusing the context

**Solutions:**

1. **Upload knowledge base first:**
   ```bash
   curl -X POST http://0.0.0.0:8000/api/v1/knowledge/upload-faqs \
     -F "file=@example_faqs.csv"
   ```

2. **Test with fresh session:**
   ```bash
   # Use a new session_id each time
   curl -X POST http://0.0.0.0:8000/api/v1/chat \
     -H "Content-Type: application/json" \
     -d '{
       "session_id": "test-'$(date +%s)'",
       "message": "What is your refund policy?",
       "user_id": "test@example.com"
     }'
   ```

3. **Check Frappe MCP server:**
   ```bash
   # Verify MCP server is running
   curl http://localhost:3000/sse
   ```

---

### 3. File Upload Errors

#### Error: "File must have 'QUESTION' and 'ANSWER' columns"

**Cause:** Excel/CSV file doesn't have required columns.

**Solution:**
```bash
# Check your file columns
python -c "import pandas as pd; print(pd.read_excel('your_file.xlsx').columns.tolist())"

# Expected output: ['SL.NO', 'QUESTION', 'ANSWER', 'Document Linkage']
```

Column names are case-insensitive, so 'question', 'QUESTION', 'Question' all work.

#### Error: "Unable to decode file"

**Cause:** Text file has invalid encoding.

**Solution:**
```bash
# Convert to UTF-8
iconv -f ISO-8859-1 -t UTF-8 input.txt > output.txt

# Or use Python
python -c "
import codecs
with codecs.open('input.txt', 'r', 'latin-1') as f:
    content = f.read()
with codecs.open('output.txt', 'w', 'utf-8') as f:
    f.write(content)
"
```

---

### 4. Connection Errors

#### Error: "Connection refused" or "Failed to connect"

**Cause:** TESS server not running.

**Solution:**
```bash
# Start TESS
./start.sh dev

# Wait for this message:
# "Application startup complete"

# Verify it's running
curl http://0.0.0.0:8000/api/v1/health
```

#### Error: "PostgreSQL connection failed"

**Cause:** PostgreSQL not running or wrong credentials.

**Solution:**
```bash
# Check PostgreSQL is running
psql -U tess_user -d tess_conversations -c "SELECT 1"

# If not running, start it
brew services start postgresql  # macOS
sudo systemctl start postgresql  # Linux

# Create database if needed
psql -U postgres -c "CREATE DATABASE tess_conversations;"
psql -U postgres -c "CREATE USER tess_user WITH PASSWORD 'your_password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE tess_conversations TO tess_user;"
```

---

### 5. ChromaDB Errors

#### Error: "Collection not found"

**Cause:** ChromaDB collection doesn't exist.

**Solution:** Collection is auto-created on first upload. Just upload your FAQs.

#### Error: "Embedding dimension mismatch"

**Cause:** Changed embedding model after creating collection.

**Solution:**
```bash
# Delete and recreate collection
rm -rf data/chromadb/*

# Then re-upload all FAQs
```

---

### 6. MCP (Frappe) Connection Errors

#### Error: "Failed to initialize Frappe MCP client"

**Cause:** Frappe MCP server not running or wrong URL.

**Solution:**
```bash
# Check MCP server URL in .env.dev
FRAPPE_MCP_URL=http://localhost:3000/sse

# Verify server is accessible
curl http://localhost:3000/sse

# Check TESS logs for MCP initialization
grep "Frappe MCP" logs/tess.log
```

#### Error: "No MCP tools loaded"

**Cause:** MCP server not returning tools.

**Solution:**
Check that your Frappe MCP server properly implements the MCP protocol and returns tools via the /sse endpoint.

---

## Debugging Commands

### Check TESS Health

```bash
curl http://0.0.0.0:8000/api/v1/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "services": {
    "chromadb": "healthy",
    "postgresql": "healthy",
    "openai": "healthy"
  }
}
```

### View Logs

```bash
# If using start.sh (console output)
# Logs are displayed in the console

# If using PM2
pm2 logs tess

# Check recent errors
grep ERROR logs/tess.log | tail -20
```

### Test Agent with Debug Logging

1. **Enable debug logging:**
   ```bash
   # In .env.dev
   LOG_LEVEL=DEBUG
   ```

2. **Restart TESS:**
   ```bash
   ./start.sh dev
   ```

3. **Make a test request:**
   ```bash
   curl -X POST http://0.0.0.0:8000/api/v1/chat \
     -H "Content-Type: application/json" \
     -d '{
       "session_id": "debug-test",
       "message": "What is your refund policy?",
       "user_id": "debug@example.com"
     }'
   ```

4. **Check logs for details:**
   ```bash
   grep "debug-test" logs/tess.log
   ```

### Check ChromaDB Contents

```bash
# Count documents in collection
python -c "
from src.vectorstore.chromadb_client import get_chroma_client
client = get_chroma_client()
print(f'Documents in ChromaDB: {client.count_documents()}')
"
```

### Test Knowledge Base Search

```bash
curl -X POST http://0.0.0.0:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "kb-test",
    "message": "search for refund",
    "user_id": "test@example.com"
  }' | jq .
```

---

## Performance Issues

### Slow Response Times

**Causes:**
- Large conversation history
- Too many FAQs being searched
- OpenAI API latency

**Solutions:**

1. **Reduce conversation history:**
   ```bash
   # In .env.dev
   MAX_CONVERSATION_HISTORY=5
   ```

2. **Reduce search results:**
   ```bash
   # In .env.dev
   CHROMA_TOP_K=3
   ```

3. **Increase similarity threshold:**
   ```bash
   # In .env.dev
   CHROMA_SIMILARITY_THRESHOLD=0.8
   ```

### High OpenAI Costs

**Solutions:**

1. **Use cheaper model:**
   ```bash
   # In .env.dev
   OPENAI_MODEL=gpt-4o-mini  # Already the cheapest
   ```

2. **Reduce max tokens:**
   ```bash
   # In .env.dev
   OPENAI_MAX_TOKENS=1000
   ```

3. **Optimize prompts:** Shorter system prompts = lower costs

---

## Getting Help

1. **Check API Documentation:**
   - Swagger: http://0.0.0.0:8000/docs
   - ReDoc: http://0.0.0.0:8000/redoc

2. **Check Logs:**
   - Console output (if using `./start.sh`)
   - `logs/tess.log` (if configured)

3. **Enable Debug Mode:**
   ```bash
   LOG_LEVEL=DEBUG
   ```

4. **Test Individual Components:**
   - PostgreSQL: `psql -U tess_user -d tess_conversations`
   - ChromaDB: Check `data/chromadb/` directory
   - OpenAI: Test API key at https://platform.openai.com/playground
   - Frappe MCP: `curl http://localhost:3000/sse`
