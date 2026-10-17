# Deep Research Pro

A multi-agent research assistant built on the OpenAI Agents SDK. Given a question, it plans a set of web searches, lets you review them, runs them in parallel, decides whether a follow-up round is needed, and writes a structured report in which every claim is cited to a numbered source.

https://github.com/user-attachments/assets/d9131a89-1591-4a9e-bf58-3f96dc60e3c0

[Watch the full-resolution demo](https://github.com/user-attachments/assets/d9131a89-1591-4a9e-bf58-3f96dc60e3c0) (1080p, 38 s)

## How it works

1. **Plan.** A query-generation agent turns the question into 3–10 search queries. You can edit, add or remove queries before the search starts.
2. **Search.** Queries run concurrently through OpenAI's hosted web search tool, and each result is summarized in parallel. Placeholder or truncated URLs in the model's output are replaced with the real links from the tool's citation annotations; sources without a usable link are dropped.
3. **Follow up.** A follow-up agent looks for gaps in what was found and issues 2–4 targeted queries for another wave (up to 3 waves).
4. **Write.** A writer agent synthesizes the top sources into a sectioned report with inline citations. The output is validated against a Pydantic schema and retried with a simpler prompt if it comes back incomplete.
5. **Explore.** The app shows the report, a sources table, an analytics dashboard (source types, top domains, citation coverage per section) and a Q&A chat that answers follow-up questions from the report and its sources.

Uploaded PDF, DOCX and TXT files are chunked, summarized and used alongside web sources. Search results are cached in memory and in SQLite for 24 hours. Reports export to Markdown, HTML and PDF, and sources to CSV.

## Running locally

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/) and an OpenAI API key.

```bash
git clone https://github.com/yavar29/GenAI_Projects.git
cd GenAI_Projects/OpenAI_Agents_SDK/deep_research_pro
uv sync
echo "OPENAI_API_KEY=sk-..." > .env
uv run streamlit run streamlit_app.py
```

A Gradio version of the UI is also available: `uv run python app.py`.

Tests: `uv run pytest`

## Project layout

```
app/agents/       query planner, follow-up decision, search summarizer, writer, report Q&A, file summarizer
app/core/         research pipeline, caching, citation rendering, retries
app/tools/        hosted web search and source URL resolution
app/schemas/      Pydantic models for plans, sources, reports and analytics
app/ui/           analytics dashboards and the Gradio app
streamlit_app.py  Streamlit app
tests/
```

## Stack

OpenAI Agents SDK, GPT-4o with hosted web search, Pydantic, asyncio, Streamlit, Plotly, SQLite, PyMuPDF, python-docx, ReportLab.
