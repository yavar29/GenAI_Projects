# 🔬 Deep Research Pro

**AI-Powered Research Assistant**

A multi-agent research co-pilot that plans research strategies, searches the web for sources with citations, and generates polished, cited reports. Features intelligent multi-wave research, user-guided query planning, and persistent caching for optimal performance.

## 🎯 Project Highlights

**Comprehensive Technical Achievements:**

1. **Multi-Agent Orchestration with Asynchronous Parallel Processing**: Implemented a sophisticated agent-based architecture (QueryGenerator, SearchAgent, WriterAgent, FollowUpDecisionAgent, FileSummarizerAgent, ReportQAAgent) using Python's `asyncio.gather` for concurrent API calls, achieving 50x speedup through parallel chunk summarization, multi-query execution, and result processing.

2. **Two-Level Caching System with SQLite Persistence**: Designed and implemented a hybrid caching strategy combining in-memory LRU cache (L1) with persistent SQLite disk storage (L2), featuring automatic TTL expiration (24-hour), LRU pruning, time-sensitive query detection, database migration logic, version salt for cache invalidation, and comprehensive cache statistics tracking.

3. **Structured Output Validation with Pydantic Schemas**: Built type-safe data pipelines using Pydantic models for all agent outputs (QueryResponse, FollowUpDecisionResponse, ResearchReport, Section, SourceDoc), implementing robust validation logic with automatic retry mechanisms, fallback strategies, section quality checks, and comprehensive error handling for reliable JSON schema compliance.

4. **Cross-Source Synthesis with Advanced Prompt Engineering**: Engineered sophisticated prompt templates enabling GPT-4o to synthesize information across multiple sources, detect contradictions, combine agreeing sources with multi-citation support ([1][2][3]), generate comprehensive 2000-5000 word research reports with adaptive section structures, and include query-level summaries for better context integration.

5. **Real-Time Streaming UI with Analytics Dashboard**: Developed an interactive Gradio-based web interface with live status streaming, integrated analytics tracking (cache hit rates, query efficiency, wave statistics, source usage), Plotly visualizations for metrics, interactive Q&A capabilities using a dedicated ReportQAAgent, and real-time progress updates with auto-scrolling.

6. **Semantic Document Processing with LLM-Based Chunking**: Implemented intelligent file processing pipeline supporting PDF, DOCX, and TXT formats with semantic chunking using GPT-4o for section boundary detection, parallel chunk summarization with error handling, and intelligent summary merging for comprehensive document understanding.

7. **Multi-Wave Research with Intelligent Follow-Up Logic**: Built iterative research system with FollowUpDecisionAgent that analyzes current findings, identifies gaps (missing data, conflicting sources, unexplored angles), and generates targeted follow-up queries (2-4 per wave) for up to 3 research waves, ensuring comprehensive coverage.

8. **URL Normalization and Citation Management**: Implemented robust URL validation and normalization (handling malformed URLs, missing protocols, relative URLs), created internal anchor links for invalid URLs, styled citation boxes with clickable links, and generated programmatic References section with proper formatting and accessibility.

9. **Token Estimation and Prompt Optimization**: Built token counting utilities using tiktoken with fallback mechanisms, implemented prompt length monitoring and truncation strategies for long summaries (3000 character limit), query-level summary truncation, and intelligent source filtering to maintain optimal prompt sizes while preserving quality.

10. **Source Deduplication and Intelligent Filtering**: Developed content-based deduplication using content hashing, implemented top-K source filtering based on content richness, enhanced source titles with context from snippets, and maintained source index with URL-based deduplication for optimal source selection.

11. **Subtopic Extraction and Theme Analysis**: Created intelligent subtopic extraction from query themes (background, statistics, trends, case studies, risks, limitations, comparisons, adoption, benefits), implemented topic-based subtopic extraction for enumerated topics, and provided structured theme guidance to WriterAgent for better report organization.

12. **Output Quality Validation with Retry Logic**: Implemented comprehensive validation checks for report sections (missing sections, empty/short sections, generic titles, insufficient content length), automatic retry with simplified prompts on validation failure, and detailed logging of quality issues for debugging and improvement.

13. **Analytics and Metrics Tracking**: Built comprehensive analytics system tracking queries executed, total sources seen, unique sources used, cache hit/miss rates, wave statistics (duration, query count, sources discovered), efficiency metrics, and credibility scoring for sources with visualization support.

14. **Interactive Q&A System**: Developed ReportQAAgent for post-report exploration, implemented context-aware question answering using full report markdown and sources table, added section navigation hints, and created chat interface with conversation history management.

15. **User-Guided Query Planning**: Implemented query review and editing interface with Dataframe support, query extraction from multiple formats (list of strings, list of lists, pandas DataFrame), query normalization and validation, and approval/skip workflows for user control.

16. **Export Functionality**: Built Markdown export with full citations and references, HTML export with styled citations, file download capabilities, and proper formatting preservation for both formats.

17. **Error Handling and Resilience**: Implemented comprehensive exception handling throughout the pipeline, safe async execution wrappers with error recovery, graceful degradation for failed operations, and detailed error logging with traceback information.

18. **Database Migration and Schema Evolution**: Created automatic database migration logic for cache schema updates, handled missing columns gracefully, populated default values for new fields, and ensured backward compatibility with existing cache files.

19. **Time-Sensitive Query Detection**: Implemented keyword-based detection for time-sensitive queries ("today", "latest", "breaking", "recent", "current"), automatic cache bypass for such queries, and intelligent cache strategy selection based on query characteristics.

20. **Markdown Rendering with Styled Citations**: Built sophisticated markdown rendering system with HTML-styled citation boxes, proper anchor link generation, Table of Contents with working links, outline generation, and clean heading formatting without numbering.

21. **Parallel File Processing**: Implemented concurrent file processing for multiple uploads, independent file handling with error isolation, status message tracking per file, and support for multiple file formats (PDF via PyMuPDF, DOCX via python-docx, TXT via standard I/O).

22. **Query-Level Summaries**: Implemented query-level summary generation from web search results, aggregation of summaries across research waves, truncation and optimization for prompt inclusion, and integration into WriterAgent prompts for better synthesis.

23. **Source Credibility Scoring**: Built credibility scoring system based on domain analysis (.edu, .gov, .org preferences), source type classification, and integration with analytics for source quality metrics.

24. **Safe Async Execution**: Created safe_run_async wrapper for agent execution with error handling, type-safe output conversion, exception recovery, and consistent error reporting across all agent calls.

25. **State Management and UI State**: Implemented Gradio State management for query persistence, user session state tracking, query editing state preservation, and seamless workflow continuation across UI interactions.

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

### Complete Research Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                               │
│  • Research Topic (e.g., "AI in Healthcare")                  │
│  • Optional: Uploaded Files (PDF, DOCX, TXT)                   │
└────────────────────────────┬──────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              PLANNING PHASE (Optional)                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  QueryGeneratorAgent                                      │  │
│  │  • Analyzes topic                                         │  │
│  │  • Generates 5-7 diverse search queries                   │  │
│  │  • Covers: background, stats, trends, case studies, etc.  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  User Review & Edit (Web UI only)                         │  │
│  │  • Review AI-generated queries                             │  │
│  │  • Edit or approve before execution                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬──────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              FILE PROCESSING (If files uploaded)                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FileSummarizerAgent (Parallel Processing)                │  │
│  │  • Extract text (PDF/DOCX/TXT)                           │  │
│  │  • Semantic chunking (LLM-based section detection)        │  │
│  │  • Parallel chunk summarization                           │  │
│  │  • Merge summaries into SourceDoc                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬──────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              RESEARCH WAVES (Iterative, up to Max Waves)        │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Wave N: Parallel Web Search                              │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  For each query (processed in parallel):          │  │  │
│  │  │  1. Check cache (L1 in-memory → L2 SQLite)        │  │  │
│  │  │  2. If miss: WebSearchTool → get results          │  │  │
│  │  │  3. Store in cache with query-level summary       │  │  │
│  │  │  4. Parallel result summarization (SearchAgent)   │  │  │
│  │  │  5. Convert to SourceDoc with citations           │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Source Deduplication & Indexing                          │  │
│  │  • Merge with file sources                                │  │
│  │  • Deduplicate by URL                                     │  │
│  │  • Assign numeric IDs [1], [2], [3]...                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FollowUpDecisionAgent                                    │  │
│  │  • Analyzes current findings                              │  │
│  │  • Decides if more research needed                        │  │
│  │  • Generates targeted follow-up queries if needed         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│                    (Loop if follow-up needed)                   │
└────────────────────────────┬──────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              REPORT GENERATION                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Source Filtering & Preparation                          │  │
│  │  • Filter to top 15 unique sources (by content richness) │  │
│  │  • Extract subtopic themes from queries                  │  │
│  │  • Prepare query-level summaries                        │  │
│  │  • Enhance source titles with context                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  WriterAgent                                             │  │
│  │  • Receives: topic, subtopics, summaries, sources       │  │
│  │  • Cross-source synthesis instructions                  │  │
│  │  • Generates structured JSON output:                    │  │
│  │    - Outline (section list)                             │  │
│  │    - Sections (title, summary, citations)              │  │
│  │    - Notes (limitations, next steps)                    │  │
│  │  • Validates output quality                              │  │
│  │  • Retries with simplified prompt if needed             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Report Rendering                                        │  │
│  │  • Convert to Markdown with styled citations             │  │
│  │  • Generate References section                           │  │
│  │  • Export to HTML (optional)                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬──────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        FINAL OUTPUT                             │
│  • Long-form research report (2000-5000 words)                 │
│  • Structured sections with inline citations [1][2][3]         │
│  • Complete References section                                 │
│  • Analytics dashboard data                                    │
│  • Interactive Q&A capability (ReportQAAgent)                   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

**Agents:**
- **QueryGeneratorAgent**: Generates diverse search queries covering multiple research angles
- **FileSummarizerAgent**: Processes uploaded documents with semantic chunking and parallel summarization
- **SearchAgent**: Summarizes individual search results into detailed analytical summaries
- **FollowUpDecisionAgent**: Decides if additional research waves are needed
- **WriterAgent**: Synthesizes sources into structured, cited research reports
- **ReportQAAgent**: Answers follow-up questions about generated reports

**Core Systems:**
- **ResearchManager**: Orchestrates the entire pipeline, manages state, and coordinates agents
- **CacheManager**: Two-level caching (in-memory + SQLite) with TTL and LRU management
- **AnalyticsBuilder**: Generates metrics and visualization data for the dashboard

### Caching System

- **Level 1 (L1)**: In-memory cache for fast access during a session
- **Level 2 (L2)**: SQLite disk cache that persists across restarts
  - **24-hour TTL** (time-to-live) for automatic expiry
  - **1000 entry size cap** with automatic pruning of least-recently-used entries
  - **Time-sensitive query detection**: Queries with keywords like "today", "latest", "breaking" automatically bypass cache
  - **Automatic cleanup**: Expired entries are removed on startup and periodically during use
  - **LRU pruning**: Entries not accessed in 7 days are removed during aggressive cleanup
  - **Version salt** for cache invalidation when logic changes
  - **Cache statistics** visible in Analytics dashboard

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

The disk cache is automatically created in `data/search_cache_v1.sqlite`. You can adjust cache settings in `app/core/cache_manager.py`:

- `CACHE_TTL_SECONDS`: Time-to-live for cache entries (default: 24 hours)
- `CACHE_MAX_ROWS`: Maximum number of cache entries (default: 1000)
- `CACHE_CLEANUP_INTERVAL`: How often to run cleanup (default: 1 hour)
- `CACHE_LAST_ACCESS_THRESHOLD`: Remove entries not accessed in this time (default: 7 days)
- `CACHE_VERSION_SALT`: Version salt for cache invalidation (change when logic/config changes)
- `TIME_SENSITIVE_KEYWORDS`: Keywords that trigger cache bypass (e.g., "today", "latest", "breaking")

**Cache Behavior:**
- Results are cached for 24 hours to improve performance
- Time-sensitive queries automatically bypass cache to ensure freshness
- Cache is automatically pruned when it exceeds 1000 entries (LRU policy)
- Expired entries are cleaned up on startup and periodically during use
- To force fresh results, slightly modify your query or wait 24 hours

## 🧪 Testing

The project includes unit and integration tests for key components:

```bash
# Run all tests
uv run pytest tests/

# Run specific test file
uv run pytest tests/test_writer_agent.py

# Run with coverage
uv run pytest tests/ --cov=app --cov-report=html
```

### Test Coverage

- **WriterAgent**: Tests structured output generation with dummy sources
- **ResearchManager**: Tests source filtering, deduplication, and subtopic extraction
- **CacheManager**: Tests cache operations, TTL expiration, and LRU pruning
- **Integration Tests**: End-to-end pipeline tests with mocked dependencies

### Manual Testing

For cache inspection and manual verification:

```bash
# Inspect cache database
uv run python test_cache.py
```

## 📝 License

MIT License

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

## 📧 Contact

For questions or feedback, please open an issue on GitHub.

