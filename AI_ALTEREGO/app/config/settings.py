import os
from dotenv import load_dotenv

load_dotenv(override=True)

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

# Notifications (optional)
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN", "")
PUSHOVER_USER  = os.getenv("PUSHOVER_USER", "")

# Knowledge Base
KB_DIR = os.getenv("KB_DIR", "kb")

# Current implementation uses CHAR-based chunking
CHUNK_MAX_CHARS      = int(os.getenv("CHUNK_MAX_CHARS", "1800"))
CHUNK_OVERLAP_CHARS  = int(os.getenv("CHUNK_OVERLAP_CHARS", "300"))

# Keep TOKEN-based knobs for future token-aware splitter (not used yet)
CHUNK_TOKENS   = int(os.getenv("CHUNK_TOKENS", "400"))
CHUNK_OVERLAP  = int(os.getenv("CHUNK_OVERLAP", "80"))

TOP_K     = int(os.getenv("TOP_K", "4"))
MAX_CHARS = int(os.getenv("MAX_CHARS", "2000"))  # cap snippet length returned by kb_search

# Optional: UI / Ops (only if you want to control Gradio from env)
GRADIO_SERVER_NAME = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
GRADIO_SERVER_PORT = int(os.getenv("GRADIO_SERVER_PORT", "7860"))

# Optional flags (handy later, safe to keep)
RAG_ENABLED    = os.getenv("RAG_ENABLED", "true").lower() == "true"
CRITIC_ENABLED = os.getenv("CRITIC_ENABLED", "false").lower() == "true"

LOG_LEVEL          = os.getenv("LOG_LEVEL", "INFO")
OPENAI_TIMEOUT_S   = int(os.getenv("OPENAI_TIMEOUT_S", "30"))
OPENAI_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
