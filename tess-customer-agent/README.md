# TESS - Technical Expert Support System

An intelligent, autonomous customer support agent built with LangGraph that seamlessly integrates ChromaDB vector search and Frappe CRM via Model Context Protocol (MCP).

## Features

- **Multi-Tool Autonomous Agent**: Automatically selects and uses the right tool for each task
- **ChromaDB Vector Search**: Semantic search over knowledge base for product information, FAQs, and documentation
- **Frappe MCP Integration**: Auto-discovers and uses Frappe CRM tools for lead management
- **PostgreSQL Memory**: Persistent conversation history with intelligent summarization
- **FastAPI REST API**: Production-ready HTTP API with OpenAPI documentation
- **Environment-Aware**: Separate configurations for dev/uat/prod environments
- **PM2 Process Management**: Cluster mode support for UAT and production deployments

## Architecture

```
User Request
     ↓
FastAPI API
     ↓
TESS Agent (LangGraph)
     ↓
Tool Router (Autonomous)
     ↓
┌─────────────────┬──────────────────┐
│  ChromaDB Tool  │  Frappe MCP Tools│
│  (Knowledge)    │  (Lead Mgmt)     │
└─────────────────┴──────────────────┘
     ↓
PostgreSQL Memory
```

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Frappe MCP Server running (http://localhost:3000/sse)
- OpenAI API key

### 1. Clone and Setup

```bash
# Navigate to project directory
cd tess-customer-agent

# Run setup script
./setup.sh dev

# This will:
# - Create virtual environment
# - Install dependencies
# - Create data directories
# - Generate .env.dev from template
```

### 2. Configure Environment

Edit `.env.dev` with your credentials:

```bash
# OpenAI
OPENAI_API_KEY=sk-your-actual-key

# PostgreSQL
POSTGRES_PASSWORD=your-postgres-password

# Frappe MCP (if authentication required)
FRAPPE_API_KEY=your-api-key
FRAPPE_API_SECRET=your-api-secret
```

### 3. Run Database Migrations

```bash
source venv/bin/activate
python -m src.utils.migrate
```

### 4. Start the Application

```bash
# Development mode (auto-reload)
./run.sh dev

# UAT mode (PM2 cluster)
./run.sh uat

# Production mode (PM2 cluster)
./run.sh prod
```

### 5. Access the API

- **API Base**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

## API Endpoints

### POST /api/v1/chat

Chat with TESS agent.

**Request:**
```json
{
  "session_id": "user-123-session",
  "message": "Tell me about your pricing",
  "user_id": "user@example.com"
}
```

**Response:**
```json
{
  "response": "Based on my knowledge base, here's what I found...",
  "session_id": "user-123-session",
  "conversation_id": "uuid",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### GET /api/v1/conversations/{session_id}

Get conversation history.

**Response:**
```json
{
  "session_id": "user-123-session",
  "conversation_id": "uuid",
  "messages": [
    {
      "role": "user",
      "content": "Hello",
      "timestamp": "2025-01-15T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help?",
      "timestamp": "2025-01-15T10:30:01Z"
    }
  ],
  "created_at": "2025-01-15T10:30:00Z",
  "message_count": 2
}
```

### POST /api/v1/index-knowledge

Index documents into knowledge base.

**Request:**
```json
{
  "documents": [
    "Product X costs $99/month and includes...",
    "Our refund policy allows..."
  ],
  "metadatas": [
    {"category": "pricing", "source": "pricing_page"},
    {"category": "policies", "source": "terms"}
  ]
}
```

**Response:**
```json
{
  "indexed": 2,
  "collection": "knowledge_base",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### GET /api/v1/health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "dev",
  "services": {
    "postgresql": "healthy",
    "chromadb": "healthy",
    "agent": "healthy"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## How It Works

### Autonomous Tool Selection

TESS automatically decides which tool to use based on user intent:

1. **User asks about products/features** → ChromaDB search tool
2. **User wants to create a lead** → Frappe MCP `create_lead` tool
3. **User checks lead status** → Frappe MCP `get_lead_status` tool
4. **User greets/chats** → Direct response (no tool)
5. **Off-topic question** → Polite redirect

### MCP Tool Auto-Discovery

TESS **never hardcodes** MCP tool names. Instead:

```python
# Tools are auto-discovered from Frappe MCP server
mcp_client = MultiServerMCPClient({
    "frappe": {
        "transport": "streamable_http",
        "url": "http://localhost:3000/sse"
    }
})

tools = await mcp_client.get_tools()  # Auto-discovers all tools
```

This means TESS automatically supports any new tools added to your Frappe MCP server without code changes.

### Conversation Memory

PostgreSQL stores:
- All conversation messages
- Tool execution history
- Conversation summaries (auto-generated after 15+ messages)
- Session metadata

Memory is automatically loaded before each agent invocation.

## Project Structure

```
tess-customer-agent/
├── src/
│   ├── agent/              # LangGraph agent
│   │   ├── graph.py        # Agent workflow
│   │   ├── nodes.py        # Agent nodes
│   │   ├── state.py        # State schema
│   │   └── prompts.py      # System prompts
│   ├── api/                # FastAPI application
│   │   ├── routes.py       # API endpoints
│   │   ├── models.py       # Request/response models
│   │   └── middleware.py   # Custom middleware
│   ├── config/             # Configuration
│   │   ├── settings.py     # Pydantic settings
│   │   └── constants.py    # Constants
│   ├── memory/             # PostgreSQL memory
│   │   ├── postgres_manager.py
│   │   └── checkpointer.py
│   ├── tools/              # Agent tools
│   │   ├── chromadb_tool.py
│   │   └── frappe_mcp.py
│   ├── vectorstore/        # ChromaDB client
│   │   ├── chromadb_client.py
│   │   └── embeddings.py
│   ├── utils/              # Utilities
│   │   ├── logging.py
│   │   ├── validators.py
│   │   └── migrate.py
│   └── main.py             # FastAPI app entry
├── migrations/             # Database migrations
├── data/                   # Data storage
│   ├── chromadb/          # Vector store
│   └── knowledge_base/    # Documents to index
├── logs/                   # Application logs
├── tests/                  # Unit tests
├── .env.{dev,uat,prod}    # Environment configs
├── requirements.txt        # Python dependencies
├── setup.sh               # Setup script
├── run.sh                 # Run script
├── ecosystem.config.js    # PM2 config
└── README.md              # This file
```

## Environment Variables

Key environment variables (see `.env.example` for full list):

```bash
# Application
APP_ENV=dev                    # dev | uat | prod
APP_PORT=8000
LOG_LEVEL=DEBUG                # DEBUG | INFO | WARNING | ERROR

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Frappe MCP
FRAPPE_MCP_URL=http://localhost:3000/sse
FRAPPE_API_KEY=                # Optional
FRAPPE_API_SECRET=             # Optional

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=tess_conversations_dev
POSTGRES_USER=tess_user
POSTGRES_PASSWORD=dev_password

# ChromaDB
CHROMA_PERSIST_DIR=./data/chromadb
CHROMA_TOP_K=5
CHROMA_SIMILARITY_THRESHOLD=0.7

# Agent
MAX_CONVERSATION_HISTORY=10
CONVERSATION_SUMMARY_THRESHOLD=15
```

## Deployment

### Development

```bash
./run.sh dev
```

Auto-reload enabled. Logs to console.

### UAT

```bash
./run.sh uat
```

Runs 2 instances via PM2. Logs to `./logs/uat-*.log`.

### Production

```bash
./run.sh prod
```

Runs 4 instances via PM2. Auto-restart enabled. Daily restart at 3 AM.

### PM2 Commands

```bash
# Status
pm2 status

# Logs
pm2 logs tess-prod

# Restart
pm2 restart tess-prod

# Stop
pm2 stop tess-prod

# Monitor
pm2 monit
```

## Indexing Knowledge Base

### Via API

```bash
curl -X POST http://localhost:8000/api/v1/index-knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "documents": ["Your product documentation here..."],
    "metadatas": [{"source": "docs", "category": "products"}]
  }'
```

### Via Python

```python
from src.tools.chromadb_tool import index_documents_from_files

# Index files from directory
await index_documents_from_files(
    file_paths=["data/knowledge_base/products.txt"],
    metadata_list=[{"category": "products"}]
)
```

## Testing

Run tests:

```bash
source venv/bin/activate
pytest tests/ -v
```

Run with coverage:

```bash
pytest tests/ --cov=src --cov-report=html
```

## Troubleshooting

### "Failed to initialize Frappe MCP client"

- Ensure Frappe MCP server is running: `curl http://localhost:3000/health`
- Check `FRAPPE_MCP_URL` in `.env.{env}`
- Verify authentication headers if required

### "PostgreSQL connection failed"

- Ensure PostgreSQL is running: `pg_isready`
- Check credentials in `.env.{env}`
- Run migrations: `python -m src.utils.migrate`

### "ChromaDB initialization failed"

- Check permissions on `data/chromadb/` directory
- Ensure sufficient disk space
- Clear ChromaDB: `rm -rf data/chromadb/*` (⚠️ deletes all indexed data)

### Agent not using tools

- Check logs for tool loading: Look for "Loaded X MCP tools"
- Verify OpenAI API key is valid
- Ensure tools are properly bound to LLM in agent graph

## Performance

- Response time: <3s (90th percentile)
- Concurrent requests: 100+ (production cluster mode)
- Memory usage: ~500MB per instance
- Database queries: Optimized with indexes

## Security

- No hardcoded credentials (all via environment variables)
- Correlation IDs for request tracking
- Input validation on all endpoints
- SQL injection protection (parameterized queries)
- Rate limiting recommended (add via API gateway)

## License

Proprietary - Internal Use Only

## Support

For issues or questions:
1. Check logs: `tail -f logs/{env}-error.log`
2. Health check: `curl http://localhost:8000/api/v1/health`
3. Contact: support@example.com
