import os, uuid
from pathlib import Path
import numpy as np

from app.config.settings import OPENAI_MODEL, KB_DIR, CHUNK_TOKENS, CHUNK_OVERLAP
from app.rag.loader import load_text_from_file, iter_kb_files
from app.rag.embedder import embed_texts
from app.rag.store import VectorStore, Chunk
from app.tools import kb_search
from app.agents.assistant import Assistant
from app.server.ui_gradio import launch_ui
from pypdf import PdfReader

def simple_token_chunks(text: str, max_chars: int = 1800, overlap: int = 300):
    # character-based splitter (simple & robust). You can swap for token-based later.
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        j = min(i + max_chars, n)
        chunks.append(text[i:j])
        i = j - overlap if j - overlap > i else j
    return [c.strip() for c in chunks if c.strip()]

def build_kb_store() -> VectorStore:
    store = VectorStore()
    for path in iter_kb_files(KB_DIR):
        raw = load_text_from_file(path)
        if not raw:
            continue
        parts = simple_token_chunks(raw)
        metas = [{"source": str(path), "section": None, "updated": None} for _ in parts]
        vecs = embed_texts(parts)
        chunks = [Chunk(id=str(uuid.uuid4()), text=t, meta=m) for t, m in zip(parts, metas)]
        store.add(vecs, chunks)
    return store

def load_me():
    # Load personal information from environment or config
    name = os.getenv("ASSISTANT_NAME", "AI Assistant")
    linkedin_text = ""
    if Path("me/linkedin.pdf").exists():
        reader = PdfReader("me/linkedin.pdf")
        for page in reader.pages:
            t = page.extract_text()
            if t: linkedin_text += t + "\n"
    summary_text = Path("me/summary.txt").read_text(encoding="utf-8") if Path("me/summary.txt").exists() else ""
    return name, summary_text, linkedin_text

if __name__ == "__main__":
    # 1) Build KB index
    store = build_kb_store()
    print(f"[KB] docs={len(store.chunks)} chunks indexed", flush=True)
    kb_search.KB_STORE = store  # expose to tool

    # 2) Load profile materials
    name, summary_text, linkedin_text = load_me()

    # 3) Spin assistant + UI
    assistant = Assistant(name=name, summary_text=summary_text, linkedin_text=linkedin_text, model=OPENAI_MODEL)
    launch_ui(assistant.chat)
