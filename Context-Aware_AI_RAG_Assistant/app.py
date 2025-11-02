import os
import uuid
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from huggingface_hub import snapshot_download  # <-- NEW

from app.config.settings import (
    OPENAI_MODEL,
    KB_DIR,
    CHUNK_MAX_CHARS,
    CHUNK_OVERLAP_CHARS,
)
from app.rag.loader import load_text_from_file, iter_kb_files
from app.rag.embedder import embed_texts
from app.rag.store import VectorStore, Chunk
from app.tools import kb_search
from app.agents.assistant import Assistant
from app.server.ui_gradio import launch_ui


# 0) pull private KB if needed
def ensure_private_kb():
    """
    If kb/ is empty or missing, pull it from a private HF repo.
    """
    kb_path = Path("kb")
    me_path = Path("me")

    # if kb exists and has files, don't download again
    if kb_path.exists() and any(kb_path.rglob("*")):
        print("[KB] Local kb/ exists, skipping download")
    else:
        print("[KB] Local kb/ missing or empty, downloading from HF...")
        token = os.getenv("HF_TOKEN")
        if not token:
            print("[KB] WARNING: HF_TOKEN not set, cannot download private KB")
        else:
            snapshot_download(
                repo_id="username/hf-repo-id",  # <-- put your private dataset/repo here
                local_dir=".",                 # download as-is into current dir
                use_auth_token=token,
            )
            print("[KB] Download complete")

    # make sure me/ exists too (some people keep me/ inside private repo)
    if not me_path.exists():
        print("[ME] me/ not found after download, you can create a public fallback here.")


def chunk_text(text: str, chunk_size: int = 1800, chunk_overlap: int = 300) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    return [c.strip() for c in chunks if c.strip()]


def build_kb_store() -> VectorStore:
    store = VectorStore()

    if len(store.chunks) > 0:
        print(f"[FAISS] Using existing vector store with {len(store.chunks)} chunks")
        return store

    print("[FAISS] Building new vector store from knowledge base...")
    for path in iter_kb_files(KB_DIR):
        raw = load_text_from_file(path)
        if not raw:
            continue

        parts = chunk_text(
            raw,
            chunk_size=CHUNK_MAX_CHARS,
            chunk_overlap=CHUNK_OVERLAP_CHARS,
        )
        metas = [{"source": str(path), "section": None, "updated": None} for _ in parts]
        vecs = embed_texts(parts)
        chunks = [
            Chunk(id=str(uuid.uuid4()), text=t, meta=m)
            for t, m in zip(parts, metas)
        ]
        store.add(vecs, chunks)

    print(f"[FAISS] Built vector store with {len(store.chunks)} chunks")
    return store


def load_me():
    name = os.getenv("ASSISTANT_NAME", "AI Assistant")

    # linkedin
    linkedin_text = ""
    linkedin_pdf = Path("me/linkedin.pdf")
    if linkedin_pdf.exists():
        reader = PdfReader(str(linkedin_pdf))
        for page in reader.pages:
            t = page.extract_text()
            if t:
                linkedin_text += t + "\n"

    # summary
    summary_path = Path("me/summary.txt")
    if summary_path.exists():
        summary_text = summary_path.read_text(encoding="utf-8")
    else:
        # fallback text if private me/ is not available
        summary_text = f"Hi, I'm {name}. This is the public version of my assistant."
    return name, summary_text, linkedin_text


# -------- STARTUP SEQUENCE (runs on import in HF) --------

# 0) make sure we have KB locally (downloads from private HF repo if needed)
ensure_private_kb()

# 1) build vector store
store = build_kb_store()
stats = store.get_stats()
print(f"[FAISS] Vector store ready: {stats['chunk_count']} chunks, dimension {stats['dimension']}", flush=True)
kb_search.KB_STORE = store

# 2) load profile
name, summary_text, linkedin_text = load_me()

# 3) create assistant + launch UI
assistant = Assistant(
    name=name,
    summary_text=summary_text,
    linkedin_text=linkedin_text,
    model=OPENAI_MODEL,
)
launch_ui(assistant.chat, assistant_instance=assistant)
