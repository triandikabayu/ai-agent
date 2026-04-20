# 🤖 Local AI Agent (LM Studio + LangGraph)

A Python-based local AI agent powered by **LM Studio** with web search, web scraping, persistent RAG knowledge base, file management, and code execution capabilities. Includes a specialized **Web Development** mode covering React, Next.js, Go, backend, databases, and more.

## Prerequisites

1. **Python 3.10+** installed
2. **LM Studio** installed and running with a model loaded
   - Download from: https://lmstudio.ai
   - Recommended models:
     - **Qwen 2.5 Coder 7B/14B** — Best for tool-calling + coding
     - **Llama 3.1 8B Instruct** — Good all-around
     - **DeepSeek Coder V2** — Great for web dev
   - Start the local server in LM Studio's **Developer** tab (default port: 1234)

## Setup

```bash
# 1. Navigate to the project
cd ai-agent

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Copy environment config (optional — defaults work out of the box)
copy .env.example .env
```

## Usage

```bash
python main.py
```

### Chat Commands

| Command | Description |
|---------|-------------|
| *(just type)* | Chat normally with the agent |
| `/search <query>` | Force a web search |
| `/scrape <url>` | Scrape a web page and display content |
| `/learn <url> [topic]` | Scrape a page and store in knowledge base |
| `/docs <url> [topic]` | Learn documentation from a URL |
| `/index <dir> [topic]` | **Index entire project directory into RAG** |
| `/knowledge <query>` | Search the stored knowledge base |
| `/knowledge <query> --topic <t>` | Search with topic filter |
| `/topics` | List all indexed topics and sources |
| `/clear-kb [topic]` | Clear knowledge (all or specific topic) |
| `/mode general` | Switch to general-purpose mode |
| `/mode web_dev` | Switch to web development expert mode |
| `/clear` | Clear conversation history |
| `/help` | Show help |
| `/exit` | Quit |

### RAG Workflow Examples

#### Index your project so the agent can read your code:
```
You: /index C:\Projects\my-nextjs-app my-app
  → Scans all source files and stores in ChromaDB

You: What components does my app use?
  → Agent searches indexed code and responds with specifics
```

#### Learn documentation for a framework:
```
You: /docs https://ui.shadcn.com/docs/components/button shadcn
You: /docs https://react.dev/learn/thinking-in-react react
You: /docs https://go.dev/doc/effective_go go

You: How do I use the shadcn Button component?
  → Agent searches stored docs and gives accurate answer
```

#### Let the agent learn autonomously:
```
You: /mode web_dev
You: I need help setting up Prisma with Next.js

  → Agent checks knowledge base first
  → If not found, searches the web
  → Scrapes Prisma docs
  → Stores key info for next time
  → Generates code with accurate patterns
```

## Architecture

```
ai-agent/
├── main.py              # CLI entry point with slash commands
├── requirements.txt     # Dependencies
├── .env / .env.example  # Configuration
│
├── agent/
│   ├── graph.py         # LangGraph agent with tool loop
│   ├── state.py         # Agent state schema
│   └── prompts.py       # System prompts (general + web_dev)
│
├── tools/
│   ├── web_search.py    # DuckDuckGo search (free)
│   ├── web_scraper.py   # BeautifulSoup web scraping
│   ├── knowledge.py     # RAG: ChromaDB + project indexing
│   ├── file_tools.py    # File read/write/list (unrestricted)
│   └── code_runner.py   # Shell command execution
│
├── config/
│   └── settings.py      # Centralized configuration
│
└── knowledge/
    └── chroma_db/       # Persistent vector storage (auto-created)
```

### 12 Tools Available

| Tool | Description |
|------|-------------|
| `search_web` | DuckDuckGo web search |
| `search_news` | DuckDuckGo news search |
| `scrape_url` | Scrape and extract page content |
| `store_knowledge` | Store text in RAG knowledge base |
| `index_project` | **Index entire project directory** |
| `search_knowledge` | Semantic search across knowledge |
| `list_knowledge_topics` | List all stored topics |
| `clear_knowledge` | Clear stored knowledge |
| `read_file` | Read any file on the system |
| `write_file` | Create/write files |
| `list_directory` | Browse directories |
| `run_command` | Execute shell commands |

## Configuration

Edit `.env` to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `LM_STUDIO_BASE_URL` | `http://localhost:1234/v1` | LM Studio server URL |
| `LM_STUDIO_MODEL` | `local-model` | Model name (LM Studio ignores this) |
| `LM_STUDIO_TEMPERATURE` | `0.7` | Response creativity (0.0-1.0) |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer for RAG |
| `CODE_RUNNER_TIMEOUT` | `30` | Max seconds for shell commands |
| `MAX_SCRAPE_LENGTH` | `8000` | Max characters from scraped pages |

## Troubleshooting

- **"Cannot connect to LM Studio"** — Make sure LM Studio is running with the Local Server enabled
- **Tool calling not working** — Some models don't support function calling; use Qwen 2.5 or Llama 3.1
- **Slow first run** — The embedding model (`all-MiniLM-L6-v2`) downloads on first use (~80MB)
- **Slow responses** — Use a smaller model (7B) or reduce temperature
- **Scraping fails** — Some sites block automated requests; try a different URL
