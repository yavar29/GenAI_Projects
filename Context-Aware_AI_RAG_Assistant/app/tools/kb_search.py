import textwrap
from typing import List
from app.config.settings import TOP_K, MAX_CHARS
from app.rag.embedder import embed_texts
from app.rag.store import VectorStore

# The store is created and hydrated in main/assistant at startup
KB_STORE: VectorStore | None = None

def kb_search(query: str, top_k: int = TOP_K):
    global KB_STORE
    if KB_STORE is None:
        return {"matches": []}
    
    # Direct search without query variations (user testing if chatbot understands queries itself)
    qvec = embed_texts([query])[0]
    results = KB_STORE.search(qvec, top_k=top_k)
    
    # Format results
    top_results = results
    
    out = []
    for score, chunk in top_results:
        snippet = chunk.text[:MAX_CHARS]
        out.append({
            "score": round(score, 4),
            "text": snippet,
            "source": chunk.meta.get("source"),
            "section": chunk.meta.get("section"),
            "updated": chunk.meta.get("updated")
        })
    return {"matches": out}


schema = {
    "name": "kb_search",
    "description": "Search the personal knowledge base for relevant passages to ground answers.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "top_k": {"type": "integer", "description": "Number of chunks to return"}
        },
        "required": ["query"],
        "additionalProperties": False
    }
}
