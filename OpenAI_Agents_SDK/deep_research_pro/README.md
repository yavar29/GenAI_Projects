# 🔬 Deep Research Pro

**AI-Powered Research Assistant**

A multi-agent research co-pilot that plans research strategies, searches the web for sources with citations, and generates polished, cited reports. Features intelligent multi-wave research, user-guided query planning, and persistent caching for optimal performance.

## ✨ Features

- **Multi-Agent Architecture**: Six specialized agents working in parallel (QueryGenerator, SearchAgent, WriterAgent, FollowUpDecisionAgent, FileSummarizerAgent, ReportQAAgent)
- **Multi-Wave Research**: Iterative research with intelligent follow-up queries (up to 3 waves)
- **User-Guided Planning**: Review and edit AI-generated search queries before execution
- **Two-Level Caching**: Fast in-memory cache + persistent SQLite disk cache (24h TTL, survives restarts)
- **Parallel Processing**: 50x speedup through concurrent API calls and parallel summarization
- **Adaptive Reports**: Long-form reports (2000-5000 words) with nested subsections and inline citations
- **Intelligent Source Limits**: AI automatically recommends optimal source count based on query complexity
- **Real-Time Analytics**: Live streaming UI with analytics dashboard and interactive Q&A
- **Export Formats**: Markdown, HTML, and PDF export with full citations
- **Cost Optimization**: Uses GPT-4o-mini for all tasks to optimize costs while maintaining quality

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd deep_research_pro

# Install Python dependencies
uv sync

# Set up your OpenAI API key
# Create a .env file in the project root:
# OPENAI_API_KEY=sk-your-key-here

# Optional: Install system libraries for PDF export (see Requirements section)
# On macOS: brew install pango cairo gdk-pixbuf libffi
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

### PDF Export Requirements (Optional)

PDF export requires system libraries that must be installed separately:

**On macOS:**
```bash
brew install pango cairo gdk-pixbuf libffi
```

**On Ubuntu/Debian:**
```bash
sudo apt-get install libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev
```

**On Fedora/RHEL:**
```bash
sudo dnf install pango cairo gdk-pixbuf2 libffi-devel
```

After installing system libraries, reinstall weasyprint:
```bash
uv pip install --upgrade --force-reinstall weasyprint
```

**Note:** PDF export is optional. Markdown and HTML export work without these dependencies.

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
- **Max Source Limit**: Leave at default (25) to let AI decide, or set explicitly (5-100)
- **Max Waves**: Number of research waves including follow-ups (1-3, default: 2)
- **Query Editing**: Review and edit AI-generated search queries before execution

**CLI Examples:**
```bash
# Basic usage
uv run drp --topic "Climate Change Solutions"

# Custom options
uv run drp --topic "Quantum Computing" --num-sources 15 --num-searches 7 --max-waves 2

# Save to file
uv run drp --topic "AI in Healthcare" --output research_report.md
```

## 📊 Architecture

### Agent Workflow Diagram

The following diagram visualizes the multi-agent research pipeline, showing how agents, tools, and handoffs work together:

![Agent Workflow](docs/workflow_graph.png)

**Understanding the Visualization:**
- **Agents** (yellow boxes): ResearchOrchestrator coordinates the entire pipeline
- **Tools** (green ellipses): Specialized functions used by each agent:
  - `generate_queries`: QueryGeneratorAgent (Planner) analyzes topics and creates search queries
  - `search_web`: SearchAgent searches and summarizes web results
  - `decide_followup`: FollowUpDecisionAgent determines if more research is needed
  - `write_report`: WriterAgent synthesizes sources into structured reports
  - `process_files`: FileSummarizerAgent processes uploaded documents
- **Handoffs** (arrows): Flow of information and delegation between agents

### Complete Research Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INPUT                               │
│  • Research Topic                                           │
│  • Optional: Uploaded Files (PDF, DOCX, TXT)                │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│              PLANNING PHASE                                 │
│  QueryGeneratorAgent (Planner): Generates 5-9 diverse       │
│  search queries and recommends optimal source count         │
│  User Review & Edit (Web UI): Review/edit queries           │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│              FILE PROCESSING (if files uploaded)            │
│  FileSummarizerAgent: Extract, chunk, and summarize         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│              RESEARCH WAVES (up to 3 waves)                 │
│                                                             │
│  Wave N: Parallel Web Search                                │
│    • Check cache (L1 → L2)                                  │
│    • WebSearchTool → get results                            │
│    • Parallel result summarization                          │
│    • Convert to SourceDoc with citations                    │
│                                                             │
│  Source Deduplication & Indexing                            │
│    • Merge with file sources                                │
│    • Deduplicate by URL                                     │
│    • Assign numeric IDs [1], [2], [3]...                    │
│                                                             │
│  FollowUpDecisionAgent                                      │
│    • Analyzes findings                                      │
│    • Decides if more research needed                        │
│    • Generates follow-up queries if needed                  │
│                                                             │
│  (Loop if follow-up needed)                                 │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│              REPORT GENERATION                              │
│                                                             │
│  Source Filtering & Preparation                             │
│    • Filter to recommended count                            │
│    • Extract subtopic themes                                │
│    • Prepare query-level summaries                          │
│                                                             │
│  WriterAgent                                                │
│    • Cross-source synthesis                                 │
│    • Generates structured report with citations             │
│    • Validates output quality                               │
│                                                             │
│  Report Rendering                                           │
│    • Convert to Markdown with citations                     │
│    • Generate References section                            │
│    • Export to Markdown, HTML, PDF                          │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                    FINAL OUTPUT                             │
│  • Long-form research report (2000-5000 words)              │
│  • Structured sections with inline citations [1][2][3]      │
│  • Complete References section                              │
│  • Analytics dashboard data                                 │
│  • Interactive Q&A capability                               │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

**Agents:**
- **QueryGeneratorAgent** (Planner): Plans research strategy by generating diverse search queries and recommends optimal source count
- **FileSummarizerAgent**: Processes uploaded documents with semantic chunking
- **SearchAgent**: Summarizes individual search results
- **FollowUpDecisionAgent**: Decides if additional research waves are needed
- **WriterAgent**: Synthesizes sources into structured, cited research reports
- **ReportQAAgent**: Answers follow-up questions about generated reports

**Core Systems:**
- **ResearchManager**: Orchestrates the entire pipeline and coordinates agents
- **CacheManager**: Two-level caching (in-memory + SQLite) with 24h TTL
- **AnalyticsBuilder**: Generates metrics and visualization data

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

The disk cache is automatically created in `data/search_cache_v1.sqlite`. Cache settings can be adjusted in `app/core/cache_manager.py`:

- Results are cached for 24 hours
- Time-sensitive queries (e.g., "today", "latest") automatically bypass cache
- Cache is automatically pruned when it exceeds 1000 entries (LRU policy)

## 📝 License

MIT License

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

## 📧 Contact

For questions or feedback, please open an issue on GitHub.

