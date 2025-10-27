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
    
    # Smart search with query variations for better results
    search_queries = generate_search_variations(query)
    all_results = []
    
    for search_query in search_queries:
        qvec = embed_texts([search_query])[0]
        results = KB_STORE.search(qvec, top_k=top_k)
        all_results.extend(results)
    
    # Remove duplicates and sort by score
    seen_texts = set()
    unique_results = []
    for score, chunk in all_results:
        if chunk.text not in seen_texts:
            seen_texts.add(chunk.text)
            unique_results.append((score, chunk))
    
    # Sort by score and take top_k
    unique_results.sort(key=lambda x: x[0], reverse=True)
    top_results = unique_results[:top_k]
    
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

def generate_search_variations(query: str) -> List[str]:
    """Generate multiple search query variations to improve recall"""
    variations = [query]
    
    # Add synonyms and related terms
    synonym_map = {
        "emergency contact": ["emergency", "contact person", "emergency contact person", "emergency contact details"],
        "work schedule": ["work hours", "working hours", "schedule", "availability", "work days"],
        "5 days a week": ["work schedule", "full time", "weekdays", "working days", "availability"],
        "willing to work": ["available to work", "can work", "work availability", "work schedule"],
        "projects": ["project", "work", "experience", "portfolio", "resume projects"],
        "not mentioned in resume": ["additional projects", "other projects", "side projects", "personal projects"],
        "work authorization": ["visa", "sponsorship", "work permit", "authorization", "OPT"],
        "relocation": ["move", "relocate", "location", "geographic"],
        "remote work": ["remote", "work from home", "telecommute", "virtual"],
        "team culture": ["work environment", "company culture", "team dynamics", "workplace"],
        "salary": ["compensation", "pay", "wage", "income", "salary expectations"],
        "start date": ["when available", "availability", "start time", "begin work"],
        "notice period": ["notice", "transition", "current job", "leaving current role"]
    }
    
    query_lower = query.lower()
    for key, synonyms in synonym_map.items():
        if key in query_lower:
            variations.extend(synonyms)
    
    # Add question variations
    if "?" in query:
        # Remove question words and try different phrasings
        question_words = ["what", "who", "when", "where", "why", "how", "can", "will", "do", "are", "is"]
        words = query.lower().split()
        filtered_words = [w for w in words if w not in question_words and w != "?"]
        if filtered_words:
            variations.append(" ".join(filtered_words))
    
    # Add specific context variations
    if "emergency" in query_lower:
        variations.extend(["contact information", "personal details", "family contact"])
    if "work" in query_lower and ("day" in query_lower or "schedule" in query_lower):
        variations.extend(["availability", "work preferences", "schedule flexibility"])
    if "project" in query_lower:
        variations.extend(["experience", "work history", "portfolio", "resume"])
    
    return list(set(variations))  # Remove duplicates

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
