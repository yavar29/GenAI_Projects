# 🔬 Deep Research Pro

**AI-Powered Research Assistant with Verification**

A verifiable, multi-agent research co-pilot that plans research strategies, crawls sources with citations, extracts structured data, verifies claims, and generates polished, cited reports.

## ✨ Features

- **Multi-Agent Architecture**: Specialized agents (Planner, Search, Writer, Verifier)
- **Parallel Search Execution**: Fast, concurrent web searches
- **Advanced Verification**: Coverage, quality, recency, and diversity metrics
- **Source Credibility Scoring**: Domain-based credibility assessment
- **Structured Outputs**: Pydantic schemas for type-safe data
- **Interactive UI**: Gradio-based web interface
- **Export Formats**: Markdown, JSON (coming soon: PDF, HTML)

## 🚀 Quick Start

### CLI Usage

```bash
# Install dependencies
uv sync

# Run with default settings
uv run -m app.run --topic "AI in Healthcare"

# Run with options
uv run -m app.run \
  --topic "AI in Healthcare" \
  --provider hosted \
  --strict-verify \
  --n 10
```

### Web UI (Gradio)

```bash
# Run the Gradio interface
uv run python app/ui/gradio_app.py

# Or use the Hugging Face Spaces entry point
uv run python app.py
```

Visit `http://localhost:7860` in your browser.

## 📋 Requirements

- Python 3.12+
- OpenAI API key (for hosted search provider)
- `uv` package manager (recommended) or `pip`

## 🔧 Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd deep_research_pro

# Install dependencies
uv sync

# Or with pip (if not using uv)
pip install -e .
```

## 🎯 Usage Examples

### Basic Research

```bash
uv run -m app.run --topic "Climate Change Solutions"
```

### With Verification

```bash
uv run -m app.run --topic "Quantum Computing" --strict-verify
```

### Using LLM Planner

```bash
# In the code, set use_sdk=True for PlannerAgent
# Or use the Gradio UI and enable "Use LLM Planner"
```

## 📊 Architecture

```
┌─────────────┐
│   Planner   │ → Creates research plan with subtopics and queries
└─────────────┘
       ↓
┌─────────────┐
│   Search    │ → Parallel web searches for sources
└─────────────┘
       ↓
┌─────────────┐
│   Writer    │ → Generates structured research report
└─────────────┘
       ↓
┌─────────────┐
│  Verifier   │ → Verifies claims with metrics
└─────────────┘
```

## 🎨 Standout Features

1. **Verification-First**: Advanced metrics (coverage, quality, recency, diversity)
2. **Multi-Agent**: Specialized agents for each task
3. **Source Credibility**: Domain-based scoring
4. **Configurable Planning**: Heuristic (fast) or SDK (smart)
5. **Structured Outputs**: Type-safe Pydantic schemas
6. **Interactive UI**: Gradio-based web interface

## 📦 Project Structure

```
deep_research_pro/
├── app/
│   ├── agents/          # Agent implementations
│   ├── core/            # Core utilities
│   ├── schemas/         # Pydantic schemas
│   ├── tools/           # Tool implementations
│   ├── ui/              # Gradio UI
│   └── run.py           # CLI entry point
├── tests/               # Test suite
├── app.py               # Hugging Face Spaces entry point
└── pyproject.toml       # Project configuration
```

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app
```

## 📝 License

MIT License

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

## 📧 Contact

For questions or feedback, please open an issue on GitHub.

