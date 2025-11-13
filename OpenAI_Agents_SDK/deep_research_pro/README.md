# 🔬 Deep Research Pro

**AI-Powered Research Assistant**

A multi-agent research co-pilot that plans research strategies, searches the web for sources with citations, and generates polished, cited reports. Features intelligent multi-wave research, user-guided query planning, and persistent caching for optimal performance.

## ✨ Features

- **Multi-Agent Architecture**: Specialized agents (Query Generator, Follow-Up Decision, Search, Writer)
- **Multi-Wave Research**: Iterative research with intelligent follow-up queries
- **User-Guided Planning**: Review and edit AI-generated search queries before execution
- **Two-Level Caching**: Fast in-memory cache + persistent SQLite disk cache (survives restarts)
- **Concurrency Guardrails**: Bounded parallelism for safe operation on Hugging Face Spaces
- **Parallel Search Execution**: Fast, concurrent web searches with query-level summaries
- **Adaptive Reports**: Long-form reports with adaptive outlines and inline citations
- **Structured Outputs**: Pydantic schemas for type-safe data
- **Interactive UI**: Gradio-based web interface with real-time Live Log streaming
- **Export Formats**: Markdown export with full citations

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd deep_research_pro

# Install dependencies
uv sync

# Set up your OpenAI API key
# Create a .env file in the project root:
# OPENAI_API_KEY=sk-your-key-here
```

### Web UI (Recommended)

```bash
# Run the Gradio interface
uv run python app/ui/gradio_app.py

# Or use the Hugging Face Spaces entry point
uv run python app.py

# Or use the launcher with environment variable support
uv run python run_gradio.py
```

Visit `http://localhost:7860` in your browser.

### CLI Usage

```bash
# Run with default settings
uv run drp --topic "AI in Healthcare"

# Or using module syntax
uv run -m app.cli --topic "AI in Healthcare"

# Run with custom options
uv run drp --topic "AI in Healthcare" --num-searches 5 --num-sources 10 --mode Smart

# Save output to file
uv run drp --topic "AI in Healthcare" --output research_report.md
```

## 📋 Requirements

- Python 3.12+
- OpenAI API key (required for web search functionality)
- `uv` package manager (recommended) or `pip`

## 🎯 Usage Examples

### Basic Research

```bash
# Using CLI
uv run drp --topic "Climate Change Solutions"

# Using Web UI
# Enter your topic in the Gradio interface and click "Start Research"
```

### Advanced Configuration

**Web UI Options:**
- **Mode**: Choose "Smart" for LLM-powered planning or "Fast" for quick heuristic planning
- **Number of Searches**: Set how many search queries to execute (3-10, default: 5)
- **Max Sources**: Limit total unique sources returned (5-20, default: 8)
- **Max Waves**: Maximum number of research waves including follow-ups (1-3, default: 3)
- **Show Outline**: Preview the report outline before final synthesis
- **Query Editing**: Review and edit AI-generated search queries before execution

**CLI Options:**
```bash
# Custom number of sources and searches
uv run drp --topic "Quantum Computing" --num-sources 15 --num-searches 7

# Fast mode (heuristic planning)
uv run drp --topic "Quantum Computing" --mode Fast

# Custom max waves for iterative research
uv run drp --topic "Quantum Computing" --max-waves 2

# Save output to file
uv run drp --topic "Quantum Computing" --output quantum_research.md
```

## 📊 Architecture

### Multi-Wave Research Pipeline

```
┌──────────────────┐
│ Query Generator  │ → Generates 3 focused initial search queries
└──────────────────┘
       ↓
┌──────────────────┐
│  Web Search      │ → Parallel searches with query-level summaries
└──────────────────┘
       ↓
┌──────────────────┐
│ Source Index     │ → Deduplicates and assigns numeric IDs
└──────────────────┘
       ↓
┌──────────────────┐
│ Per-Result       │ → Summarizes each source (Title/URL/Snippet)
│ Summarization    │
└──────────────────┘
       ↓
┌──────────────────┐
│ Follow-Up        │ → Decides if more research needed
│ Decision Agent   │
└──────────────────┘
       ↓ (if needed, up to Max Waves)
┌──────────────────┐
│  Follow-Up       │ → Targeted searches for gaps
│  Searches        │
└──────────────────┘
       ↓
┌──────────────────┐
│  Writer Agent    │ → Generates adaptive long-form report
└──────────────────┘
```

### Caching System

- **Level 1 (L1)**: In-memory cache for fast access during a session
- **Level 2 (L2)**: SQLite disk cache that persists across restarts
  - 24-hour TTL (time-to-live) for automatic expiry
  - 1000 entry size cap
  - Version salt for cache invalidation when logic changes

## 🎨 Standout Features

1. **Multi-Wave Research**: Iterative research process with intelligent follow-up queries
   - Query Generator creates focused initial queries
   - Follow-Up Decision Agent determines if more research is needed
   - Up to 3 waves of research for comprehensive coverage

2. **User-Guided Planning**: Review and edit AI-generated search queries
   - See the AI's reasoning for query selection
   - Edit queries before execution
   - Approve or skip to use original queries

3. **Two-Level Caching System**:
   - Fast in-memory cache for session performance
   - Persistent SQLite disk cache (survives restarts)
   - Automatic expiry (24h TTL) and size management
   - Cache statistics visible in Live Log

4. **Concurrency Guardrails**: Safe operation on Hugging Face Spaces
   - Bounded parallelism for searches (default: 5 concurrent)
   - Bounded parallelism for summarization (default: 5 concurrent)
   - Prevents rate limiting and resource exhaustion

5. **Adaptive Reports**: Long-form reports with intelligent structure
   - Adaptive outlines based on query intent
   - Comprehensive depth (typically 2000-5000 words)
   - Deterministic numeric citations [1], [2], [3]
   - Programmatically generated References section

6. **Real-Time Live Log**: Streaming status updates
   - Step-by-step progress tracking
   - Cache hit/miss statistics
   - Outline preview option
   - Full internal working details

7. **Structured Outputs**: Type-safe Pydantic schemas for reliable data handling

8. **Parallel Search**: Fast, concurrent web searches with query-level summaries

## 📦 Project Structure

```
deep_research_pro/
├── app/
│   ├── agents/          # Agent implementations
│   │   ├── planner_agent.py    # QueryGeneratorAgent, FollowUpDecisionAgent
│   │   ├── search_agent.py     # Per-result summarizer
│   │   └── writer_agent.py     # Report generation
│   ├── core/            # Core utilities
│   │   ├── research_manager.py # Main orchestration + caching
│   │   ├── render.py           # Markdown rendering
│   │   ├── retry.py            # Retry utilities
│   │   ├── openai_client.py    # Hardened OpenAI client
│   │   └── tracing.py          # Trace dashboard URL
│   ├── schemas/         # Pydantic schemas
│   │   ├── plan.py             # QueryResponse, FollowUpDecisionResponse
│   │   ├── report.py           # ResearchReport, Section
│   │   └── source.py           # SourceItem, SourceDoc, SearchResult
│   ├── tools/           # Tool implementations
│   │   └── hosted_tools.py     # OpenAI WebSearchTool wrapper
│   ├── ui/              # Gradio UI
│   │   └── gradio_app.py       # Web interface with Live Log
│   └── cli.py           # CLI entry point
├── data/                # Generated reports, exports, and cache
│   └── search_cache_v1.sqlite  # SQLite disk cache (auto-created)
├── app.py               # Hugging Face Spaces entry point
├── run_gradio.py        # Gradio launcher with environment variable support
└── pyproject.toml       # Project configuration
```

## 🔧 Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `GRADIO_SERVER_NAME`: Server hostname (default: "0.0.0.0")
- `GRADIO_SERVER_PORT`: Server port (default: 7860)
- `GRADIO_SHARE`: Enable public sharing (default: false)
- `GRADIO_AUTH`: Authentication in format "username:password" (optional)

### Cache Configuration

The disk cache is automatically created in `data/search_cache_v1.sqlite`. You can adjust cache settings in `app/core/research_manager.py`:

- `CACHE_TTL_SECONDS`: Time-to-live for cache entries (default: 24 hours)
- `CACHE_MAX_ROWS`: Maximum number of cache entries (default: 1000)
- `CACHE_VERSION_SALT`: Version salt for cache invalidation (change when logic/config changes)

## 📝 License

MIT License

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

## 📧 Contact

For questions or feedback, please open an issue on GitHub.

