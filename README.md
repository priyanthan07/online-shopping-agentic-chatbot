# Grocery Shopping Agentic Chatbot

A production-grade AI-powered chatbot for online grocery shopping built with a multi-agent architecture, RAG (Retrieval-Augmented Generation), and MCP (Model Context Protocol) integration.

## Overview

This chatbot system provides intelligent customer support for an online grocery store with capabilities including:

- **FAQ Support**: Answer questions about policies, delivery, returns, and payment methods
- **Product Search**: Natural language product queries with intelligent matching
- **Shopping Actions**: Budget calculations, price checks, and cart management
- **Refund Processing**: Automated refund request handling with validation
- **Stock Checking**: Real-time inventory queries via MCP server
- **Safety Guardrails**: Content filtering, PII detection, and business rule validation
- **Monitoring**: Complete observability with Langfuse integration

## Architecture

### Multi-Agent System

- **Orchestrator Agent**: Routes requests to appropriate sub-agents based on intent
- **FAQ Agent**: Handles policy and information queries using RAG
- **Action Agent**: Processes transactional requests (refunds, budgets, stock checks)

### Technology Stack

- **Framework**: LangChain/LangGraph for agent orchestration
- **LLM**: OpenAI GPT-4o
- **Vector Database**: ChromaDB for RAG retrieval
- **MCP Server**: FastMCP for stock price tool integration
- **Monitoring**: Langfuse for tracing and evaluation
- **UI**: Streamlit web interface
- **Deployment**: Docker Compose

### Tools & Capabilities

1. **create_refund** (LangChain tool): Process refund requests with validation
2. **calculate_budget** (LangChain tool): Calculate what items fit within budget
3. **get_stock_price** (MCP tool): Query real-time stock and pricing from MCP server

### Data Sources

All evaluation and mock data are located in the `/data` directory:

- `faqs.json` - Frequently asked questions
- `products.json` - Product catalog
- `policies.json` - Store policies
- `orders.json` - Customer orders for refund validation
- `stock.json` - Inventory data for MCP server
- `evaluation_tests.json` - Ground truth test cases for auto-evaluation

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- OpenAI API key
- Langfuse account

### Setup

1. **Clone the repository** (or extract the project files)

2. **Create `.env` file** in the project root with the following:

```env
OPENAI_API_KEY=your_openai_api_key_here
MODEL_NAME=gpt-4o

LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

3. **Build the Docker containers**:

```bash
docker-compose build --no-cache
```

4. **Start the application**:

```bash
docker-compose up
```

5. **Access the chatbot**:

Open your browser and navigate to: `http://localhost:8501`

### Stopping the Application

```bash
docker-compose down
```

## Services

The application runs two Docker services:

### 1. MCP Server (`mcp-server`)
- **Port**: 8001
- **Purpose**: Provides stock price checking tool via Model Context Protocol
- **Endpoint**: `http://mcp-server:8001` (internal Docker network)

### 2. Chatbot Application (`chatbot`)
- **Port**: 8501
- **Purpose**: Main Streamlit web interface and agent orchestration
- **Features**: 
  - Interactive chat interface
  - Example query buttons
  - Auto-evaluation dashboard
  - Session management

## Features

### 1. Multi-Turn Conversations
- Context-aware responses
- Session-based conversation history
- Intelligent routing between specialized agents

### 2. RAG-Powered Responses
- Vector similarity search using ChromaDB
- Document chunking and embedding
- Context-enriched answers for FAQs and product queries

### 3. Safety Guardrails
- **Content Filtering**: Blocks inappropriate content using LLM-based moderation
- **PII Detection**: Identifies and handles sensitive personal information
- **Refund Validation**: Maximum refund limits and order existence checks
- **Budget Constraints**: Validates purchase amounts against budget

### 4. Auto-Evaluation
- Built-in evaluation suite with ground truth test cases
- Performance metrics: pass rate, average score, latency
- Accessible via "Evaluate" button in the UI

### 5. Monitoring & Observability
- Langfuse integration for:
  - Request tracing
  - Token usage tracking
  - Latency monitoring
  - Error tracking
  - Agent performance analytics

## Example Queries

### FAQ Queries
- "What's your return policy?"
- "Do you deliver on weekends?"
- "What payment methods do you accept?"

### Shopping Actions
- "How much does milk cost?"
- "Can I buy milk and bread for $10?"
- "Check stock for product P001"

### Budget & Refunds
- "Can I afford rice, chicken, and eggs within $30?"
- "Create a refund for order ORD001"
- "I need a refund for order ORD005"

### Edge Cases
- "Check stock for product P007" (out of stock)
- "Create a refund for ORD999" (invalid order)
- "I want a refund for order ORD006" (exceeds $1000 limit)

## Project Structure

```
📦online-shopping-agentic-chatbot
 ┣ 📂.git
 ┃ ┣ 📜.gitignore
 ┃ ┣ 📜.lock
 ┃ ┣ 📜CACHEDIR.TAG
 ┃ ┗ 📜pyvenv.cfg
 ┣ 📂chroma_db
 ┣ 📂data
 ┃ ┣ 📜eval_qa_pairs.json
 ┃ ┣ 📜faqs.json
 ┃ ┣ 📜orders.json
 ┃ ┣ 📜policies.json
 ┃ ┣ 📜products.json
 ┃ ┗ 📜stock.json
 ┣ 📂logs
 ┣ 📂mcp_server
 ┃ ┣ 📜server.py
 ┃ ┗ 📜__init__.py
 ┣ 📂src
 ┃ ┣ 📂agents
 ┃ ┃ ┣ 📜action_agent.py
 ┃ ┃ ┣ 📜faq_agent.py
 ┃ ┃ ┣ 📜orchestrator.py
 ┃ ┃ ┗ 📜__init__.py
 ┃ ┣ 📂guardrails
 ┃ ┃ ┣ 📜safety.py
 ┃ ┃ ┗ 📜__init__.py
 ┃ ┣ 📂monitoring
 ┃ ┃ ┣ 📜evaluator.py
 ┃ ┃ ┣ 📜logger.py
 ┃ ┃ ┗ 📜__init__.py
 ┃ ┣ 📂rag
 ┃ ┃ ┣ 📜ingestion.py
 ┃ ┃ ┣ 📜retriever.py
 ┃ ┃ ┗ 📜__init__.py
 ┃ ┣ 📂tools
 ┃ ┃ ┣ 📜grocery_tools.py
 ┃ ┃ ┣ 📜mcp_tool.py
 ┃ ┃ ┗ 📜__init__.py
 ┃ ┣ 📜config.py
 ┃ ┗ 📜main.py
 ┣ 📜.dockerignore
 ┣ 📜.env
 ┣ 📜.env.example
 ┣ 📜.gitignore
 ┣ 📜.python-version
 ┣ 📜app.py
 ┣ 📜docker-compose.yml
 ┣ 📜Dockerfile
 ┣ 📜Dockerfile.mcp
 ┣ 📜LICENSE
 ┣ 📜pyproject.toml
 ┣ 📜README.md
 ┗ 📜uv.lock
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Yes | - |
| `MODEL_NAME` | OpenAI model to use | No | `gpt-4o` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | No | - |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | No | - |
| `LANGFUSE_BASE_URL` | Langfuse server URL | No | `https://cloud.langfuse.com` |

### Safety Configuration

Configured in `src/config.py`:

- `MAX_REFUND_AMOUNT`: Maximum refund allowed (default: $1000.0)
- `RESTRICTED_TOPICS`: Content filtering topics



### Vector Database

ChromaDB data is persisted in the `chroma_db/` directory. On first run, the system will:
1. Load documents from `/data` directory
2. Create embeddings using OpenAI's `text-embedding-3-small`
3. Store vectors in ChromaDB
4. Subsequent runs will use the existing vector store

## Evaluation

The system includes a comprehensive auto-evaluation framework:

1. **Click "Evaluate" button** in the Streamlit UI
2. System runs all test cases from `data/evaluation_tests.json`
3. Results show:
   - Overall pass rate
   - Per-test scores and latency
   - Agent routing decisions
   - Detailed response analysis

## Troubleshooting

### MCP Connection Errors

If you see "All connection attempts failed":
- Ensure MCP server is running: check `docker-compose logs mcp-server`
- Verify MCP server binds to `0.0.0.0:8001` (not `127.0.0.1`)
- Check Docker network connectivity

### Vector Store Issues

If RAG retrieval fails:
- Delete `chroma_db/` directory and restart to rebuild
- Check that all JSON files exist in `/data` directory

### API Rate Limits

If hitting OpenAI rate limits:
- Reduce concurrent requests
- Consider using a lower-tier model for development
- Implement request throttling
