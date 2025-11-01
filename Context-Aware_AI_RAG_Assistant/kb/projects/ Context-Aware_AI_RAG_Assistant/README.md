# Context-Aware AI RAG Assistant (Project Documentation)

An intelligent personal assistant that embodies a professional persona, answers questions grounded in your knowledge base, and adapts tone by audience.

## What this project does

- Retrieval-Augmented Generation (RAG) over `kb/` (FAQ, resume, projects, portfolio)
- Persona switching (Professional, Mentor, Casual, Technical)
- Function-calling tools for unknown questions and user-intent capture
- Persistent FAISS vector store for fast semantic search
- Optional Pushover notifications for follow-ups

## Why it exists

To provide a trustworthy, always-on representation of you that answers personal and professional questions with sourced, current information.

## Core architecture

- UI: Gradio app (`app/server/`), served by `main.py`
- Agents: Conversational orchestration (`app/agents/`)
- RAG: Chunking + embeddings + FAISS (`app/rag/`, `vector_store/`)
- Personas and prompts: System behavior and style (`app/core/`)
- Tools: Knowledge lookup, logging, notifications (`app/tools/`)

High-level flow:
1. User asks a question in Gradio
2. Router builds retrieval query → fetches top chunks from FAISS
3. LLM answers with grounded context and selected persona
4. If the question is unknown or contact intent is detected, tools log and optionally notify via Pushover

## RAG details

- Source directories: `kb/faq/`, `kb/projects/`, `kb/resume/`, `kb/portfolio/`, `me/`
- Document Loading: LangChain loaders (PyPDFLoader for PDFs, TextLoader for text files)
- Chunking: LangChain's `RecursiveCharacterTextSplitter` with `CHUNK_MAX_CHARS` and `CHUNK_OVERLAP_CHARS` configurable via env
- Embeddings: OpenAI embeddings, indexed in FAISS (`vector_store/` persisted)
- On startup: Loads existing FAISS index or builds from `KB_DIR`

## Persona switching

Four presets: Professional, Mentor, Casual, Technical. Each adjusts tone, verbosity, and structure; content remains grounded by RAG.

## Notifications (optional)

Pushover can notify when:
- A user asks an unknown question
- A user shares contact details or intent to connect

Set `PUSHOVER_TOKEN` and `PUSHOVER_USER` to enable.

## Configuration (env)

```
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4
KB_DIR=./kb
CHUNK_TOKENS=1800
CHUNK_OVERLAP=300
GRADIO_SERVER_PORT=7861
# Optional Pushover
PUSHOVER_TOKEN=...
PUSHOVER_USER=...
```

## How to extend

- Add content: Place markdown/PDFs under `kb/` and restart; FAISS refreshes
- Add personas: Edit `app/core/personas.py` or `persona_config.json`
- Tune retrieval: Adjust chunk sizes and overlap in env; rebuild index

## Implementation FAQ (for RAG to answer)

Q: How does the assistant decide what context to retrieve?
A: It builds a semantic query from the user input, embeds it, and performs kNN over FAISS to fetch top-k chunks from `KB_DIR` before composing the answer.

Q: Where is the vector index stored and how is it persisted?
A: In `vector_store/` as a FAISS index plus metadata. On startup the app loads it if present; otherwise it builds and saves it.

Q: What happens with questions not covered in the knowledge base?
A: The assistant logs the unknown question via a tool call. If Pushover is configured, it sends a notification for follow-up. It may also ask the user for clarification or contact details.

Q: How does persona switching affect answers?
A: The same grounded facts are presented with different tones, structure, and emphasis to suit Professional, Mentor, Casual, or Technical audiences.

Q: How do I add new projects so they’re discoverable?
A: Create a folder under `kb/projects/<your-project>/README.md`. The RAG pipeline indexes it and citations can point to those files.

Q: Which model powers generation?
A: Configurable via `OPENAI_MODEL` (defaults to `gpt-4`). Retrieval uses OpenAI embeddings.

Q: How can I verify sources in answers?
A: Enable citation rendering in the UI or prompt template; retrieved chunk metadata includes file paths (e.g., `kb/projects/AI-Alter-Ego/README.md`).

---

This document exists under `kb/projects/AI-Alter-Ego/README.md` so the assistant can cite it when asked about its own implementation.

## GitHub

- Profile: https://github.com/yavar29
- Repository: https://github.com/yavar29/GenAI_Projects/tree/main/Context-Aware_AI_RAG_Assistant


