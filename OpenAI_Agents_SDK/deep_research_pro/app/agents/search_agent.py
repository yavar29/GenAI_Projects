from __future__ import annotations
from typing import Callable, Iterable, List, Dict
from urllib.parse import urlparse

from app.schemas.source import SourceDoc

SearchFunc = Callable[[str], List[Dict]]

class SearchAgent:
    """
    Iteration 1A: tool-agnostic search.
    - Accepts a search function that takes a query and returns a list of dicts like:
      [{"title": "...", "url": "...", "snippet": "...", "published": "...", "provider": "..."}]
    - Normalizes to SourceDoc and deduplicates by URL.
    In Iteration 1B, we'll plug the OpenAI hosted WebSearchTool here.
    """
    def __init__(self, search_func: SearchFunc):
        self.search_func = search_func

    def _normalize(self, raw: Dict) -> SourceDoc:
        title = raw.get("title") or raw.get("name") or "Untitled"
        url = raw.get("url") or raw.get("link") or "https://example.com"
        snippet = raw.get("snippet") or raw.get("summary") or ""
        published = raw.get("published") or raw.get("date")
        provider = raw.get("provider")
        # Best-effort source_type based on domain
        try:
            netloc = urlparse(url).netloc.lower()
        except Exception:
            netloc = ""
        source_type = "news" if any(k in netloc for k in ["news", "cnn", "bbc", "reuters"]) else "web"
        return SourceDoc(title=title, url=url, snippet=snippet, published=published, source_type=source_type, provider=provider)

    def search_many(self, queries: Iterable[str], limit_total: int = 8) -> List[SourceDoc]:
        bag: Dict[str, SourceDoc] = {}
        for q in queries:
            try:
                results = self.search_func(q) or []
            except Exception:
                results = []
            for r in results:
                try:
                    doc = self._normalize(r)
                    if str(doc.url) not in bag:
                        bag[str(doc.url)] = doc
                except Exception:
                    continue
                if len(bag) >= limit_total:
                    break
            if len(bag) >= limit_total:
                break
        return list(bag.values())
