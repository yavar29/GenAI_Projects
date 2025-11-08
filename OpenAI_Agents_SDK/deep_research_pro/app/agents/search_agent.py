from __future__ import annotations
import asyncio
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
        title = (raw.get("title") or raw.get("name") or "").strip()
        url = raw.get("url") or raw.get("link") or "https://example.com"
        snippet = (raw.get("snippet") or raw.get("summary") or "").strip()
        published = raw.get("published") or raw.get("date")
        provider = raw.get("provider")
        # Best-effort source_type based on domain
        try:
            netloc = urlparse(url).netloc.lower()
        except Exception:
            netloc = ""
        source_type = "news" if any(k in netloc for k in ["news", "cnn", "bbc", "reuters"]) else "web"
        return SourceDoc(title=title, url=url, snippet=snippet, published=published, source_type=source_type, provider=provider)

    async def search_one_async(self, query: str) -> List[SourceDoc]:
        # Run the provided (possibly sync) search function in a worker thread
        raw_results = await asyncio.to_thread(self.search_func, query)
        # Normalize dicts to SourceDoc objects
        normalized: List[SourceDoc] = []
        for raw in raw_results or []:
            try:
                doc = self._normalize(raw)
                normalized.append(doc)
            except Exception:
                continue
        return normalized

    async def search_many_async(self, queries: Iterable[str], limit_total: int = 8) -> List[SourceDoc]:
        tasks = [asyncio.create_task(self.search_one_async(q)) for q in queries]
        results: List[SourceDoc] = []
        seen = set()
        for t in asyncio.as_completed(tasks):
            try:
                batch = await t
            except Exception:
                batch = []
            for s in batch:
                key = (s.title, str(s.url))
                if key not in seen:
                    seen.add(key)
                    results.append(s)
                    if len(results) >= limit_total:
                        return results
        return results

    def search_many(self, queries: Iterable[str], limit_total: int = 8) -> List[SourceDoc]:
        """Sync wrapper for search_many_async (for backward compatibility)."""
        return asyncio.run(self.search_many_async(queries, limit_total=limit_total))
