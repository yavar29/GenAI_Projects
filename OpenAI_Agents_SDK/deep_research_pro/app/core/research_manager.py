"""
ResearchManager: Orchestrates the multi-wave research pipeline.
Similar to reference coordinator.py with Query Generator and Follow-Up Decision.
"""

from __future__ import annotations
from typing import List, Optional, AsyncIterator, Tuple, Dict
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import asyncio
import sqlite3
import json
import time
import os
from agents import trace, gen_trace_id
from openai import AsyncOpenAI

from app.core.tracing import TRACE_DASHBOARD
from app.core.openai_client import make_async_client
from app.core.settings import OPENAI_API_KEY
from app.tools.hosted_tools import get_search_provider_async
from app.agents.planner_agent import QueryGeneratorAgent, FollowUpDecisionAgent
from app.agents.search_agent import SearchAgent
from app.agents.writer_agent import WriterAgent
from app.schemas.plan import QueryResponse, FollowUpDecisionResponse
from app.schemas.report import ResearchReport
from app.schemas.source import SourceItem, SourceDoc, SearchResult
from app.core.render import render_markdown

# Configuration constants
MAX_WAVES = 3  # Maximum number of research waves (Wave 1 + up to 2 follow-ups)
TOPK_PER_QUERY = 5  # Top results per query from WebSearchTool
MAX_SOURCES_FINAL = 20  # Maximum total sources across all waves

# Concurrency guardrails (safe defaults for HF Spaces)
SEARCH_CONCURRENCY = 5
SUMMARY_CONCURRENCY = 5

# Disk cache configuration
CACHE_TTL_SECONDS = 24 * 3600  # 24h
CACHE_MAX_ROWS = 1000  # cap on-disk cache
CACHE_DB_PATH = os.path.join("data", "search_cache_v1.sqlite")
CACHE_VERSION_SALT = "hosted-v1-topk5"  # change when semantics/config change


def _ensure_cache_db(path: str):
    """Initialize SQLite cache database and return connection."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS qcache (
            k TEXT PRIMARY KEY,
            v TEXT NOT NULL,
            ts INTEGER NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS qcache_ts_idx ON qcache(ts)")
    conn.commit()
    return conn


def _cache_key(norm_q: str) -> str:
    """Generate cache key with version salt."""
    # include salt so changing TOPK, provider, or schema invalidates old rows
    return f"{CACHE_VERSION_SALT}|{norm_q}"


def _cache_get_disk(conn, norm_q: str):
    """Get cached value from disk (L2 cache). Returns None if miss or expired."""
    k = _cache_key(norm_q)
    row = conn.execute("SELECT v, ts FROM qcache WHERE k=?", (k,)).fetchone()
    if not row:
        return None
    v_json, ts = row
    if (time.time() - ts) > CACHE_TTL_SECONDS:
        # expired; best-effort purge
        conn.execute("DELETE FROM qcache WHERE k=?", (k,))
        conn.commit()
        return None
    try:
        return json.loads(v_json)
    except Exception:
        return None


def _cache_set_disk(conn, norm_q: str, payload: dict):
    """Store value in disk cache (L2 cache) with size cap."""
    k = _cache_key(norm_q)
    v_json = json.dumps(payload, ensure_ascii=False)
    now = int(time.time())
    conn.execute("INSERT OR REPLACE INTO qcache(k, v, ts) VALUES(?,?,?)", (k, v_json, now))
    # naive size cap
    conn.execute("""
        DELETE FROM qcache WHERE k IN (
            SELECT k FROM qcache ORDER BY ts ASC LIMIT
            CASE WHEN (SELECT COUNT(*) FROM qcache) > ? THEN (SELECT COUNT(*) - ?) ELSE 0 END
        )
    """, (CACHE_MAX_ROWS, CACHE_MAX_ROWS))
    conn.commit()


class ResearchManager:
    """
    Orchestrates the multi-wave research pipeline:
    - Wave 1: Query Generator → Search → Summarize each result
    - Follow-up waves: Follow-up Decision → Search → Summarize new results
    - Synthesis: Format findings → Writer
    Uses async generator pattern to yield status updates throughout the process.
    """
    
    def __init__(
        self,
        openai_client: Optional[AsyncOpenAI] = None,
        num_searches: int = 5,
        num_sources: int = 8,
        max_waves: int = MAX_WAVES,
    ):
        """
        Initialize ResearchManager.
        
        Args:
            openai_client: Hardened OpenAI client (creates one if not provided)
            num_searches: Number of search queries to perform (default: 5) - kept for compatibility
            num_sources: Maximum number of sources to return (default: 8)
            max_waves: Maximum number of research waves (default: 3)
        """
        self.openai_client = openai_client or make_async_client()
        self.num_searches = num_searches
        self.num_sources = num_sources
        self.max_waves = max_waves
        self.provider = "hosted"  # Always use hosted for real search
        
        # Ensure API key is in environment for Agents SDK
        if OPENAI_API_KEY and not hasattr(self, '_api_key_set'):
            os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
            self._api_key_set = True
        
        # --- Caching & guardrails ---
        # Cache: normalized_query -> (results_list, query_summary_or_None)
        self._search_cache: Dict[str, Tuple[List[dict], Optional[str]]] = {}
        
        # Concurrency semaphores (tunable via constants above)
        self._search_sem = asyncio.Semaphore(SEARCH_CONCURRENCY)
        self._summary_sem = asyncio.Semaphore(SUMMARY_CONCURRENCY)
        
        # Simple counters for Live Log visibility
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Disk cache (level-2)
        self._disk_cache_conn = _ensure_cache_db(CACHE_DB_PATH)
    
    async def generate_plan(self, query: str) -> QueryResponse:
        """
        Generate initial search plan (queries) for user review.
        
        Args:
            query: Research topic/query
            
        Returns:
            QueryResponse with thoughts and queries
        """
        query_gen = QueryGeneratorAgent(openai_client=self.openai_client)
        return await query_gen.generate_async(query)
    
    async def run(self, query: str, approved_queries: Optional[List[str]] = None) -> AsyncIterator[Tuple[str, List, str]]:
        """
        Run the complete research pipeline.
        Yields status updates and final results as tuples: (report_md, sources_data, status)
        
        Args:
            query: Research topic/query
            approved_queries: Optional list of pre-approved queries (if None, generates them)
            
        Yields:
            Tuple of (report_markdown, sources_data, status_text)
        """
        if not query or not query.strip():
            yield ("", [], "❌ Please enter a research topic")
            return
        
        # Generate trace ID (like reference)
        trace_id = gen_trace_id()
        trace_url = f"{TRACE_DASHBOARD}{trace_id}"
        
        status = ["🔄 Initializing..."]
        
        # Reset per-run cache and counters
        self._search_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        
        yield ("", [], "\n\n".join(status))
        
        try:
            # Check API key
            if not OPENAI_API_KEY:
                yield ("", [], "❌ Error: OPENAI_API_KEY not set.\n\nPlease check:\n1. Your .env file exists in the project root\n2. It contains: OPENAI_API_KEY=sk-...\n3. The API key is valid and not expired")
                return
            
            # Verify API key format
            if not OPENAI_API_KEY.startswith(("sk-", "sk-proj-")):
                yield ("", [], f"❌ Error: Invalid API key format. Should start with 'sk-' or 'sk-proj-'\n\nCurrent key starts with: {OPENAI_API_KEY[:10] if len(OPENAI_API_KEY) > 10 else 'too short'}...")
                return
            
            # Start trace (using reference format)
            with trace("Research trace", trace_id=trace_id):
                # Trace URL already has https:// prefix, so Gradio will auto-link it
                status.append(f"🔗 Trace: {trace_url}")
                yield ("", [], "\n\n".join(status))
                
                # WAVE 1: Use approved queries or generate them
                if approved_queries:
                    # Use pre-approved queries
                    queries = approved_queries
                    status.append(f"✅ Using {len(queries)} approved queries")
                    yield ("", [], "\n\n".join(status))
                else:
                    # Generate queries (legacy path, for CLI)
                    status.append("📋 Generating initial search queries...")
                    yield ("", [], "\n\n".join(status))
                    
                    query_gen = QueryGeneratorAgent(openai_client=self.openai_client)
                    query_response = await query_gen.generate_async(query)
                    queries = query_response.queries
                    status.append(f"✅ Generated {len(queries)} queries")
                    yield ("", [], "\n\n".join(status))
                
                # Perform Wave 1 searches
                status.append(f"🔍 Wave 1: Searching {len(queries)} queries...")
                yield ("", [], "\n\n".join(status))
                
                source_index: Dict[str, SourceItem] = {}  # URL -> SourceItem (for deduplication)
                all_summaries: List[SearchResult] = []  # All summaries from all waves
                query_level_summaries: List[str] = []  # Query-level summaries from hosted search
                
                # Search and build source index
                hits, query_summaries = await self._web_search_many(queries)
                status.append(f"📦 Cache: {self._cache_hits} hits • {self._cache_misses} misses • {len(self._search_cache)} entries")
                yield ("", [], "\n\n".join(status))
                
                query_level_summaries.extend(query_summaries)
                source_index = self._build_source_index(hits, source_index)
                status.append(f"✅ Wave 1: Found {len(source_index)} unique sources")
                yield ("", [], "\n\n".join(status))
                
                # Summarize each result
                status.append("📝 Summarizing search results...")
                yield ("", [], "\n\n".join(status))
                
                wave1_summaries = await self._summarize_each_source(list(source_index.values()))
                all_summaries.extend(wave1_summaries)
                status.append(f"✅ Summarized {len(wave1_summaries)} results")
                yield ("", [], "\n\n".join(status))
                
                # FOLLOW-UP WAVES
                iteration = 1
                while iteration < self.max_waves:
                    # Build findings text for follow-up decision
                    findings_text = self._join_findings(query, source_index, all_summaries)
                    
                    status.append(f"🤔 Evaluating if more research is needed (iteration {iteration + 1})...")
                    yield ("", [], "\n\n".join(status))
                    
                    followup_agent = FollowUpDecisionAgent(openai_client=self.openai_client)
                    decision = await followup_agent.decide_async(query, findings_text)
                    
                    if not decision.should_follow_up:
                        status.append("✅ Research complete—no follow-up needed")
                        yield ("", [], "\n\n".join(status))
                        break
                    
                    iteration += 1
                    status.append(f"🔍 Wave {iteration}: Conducting follow-up research...")
                    yield ("", [], "\n\n".join(status))
                    
                    # Track max ID before merging to identify new sources
                    max_id_before = max([s.id for s in source_index.values()], default=0)
                    
                    # Perform follow-up searches
                    hits2, followup_query_summaries = await self._web_search_many(decision.queries)
                    status.append(f"📦 Cache: {self._cache_hits} hits • {self._cache_misses} misses • {len(self._search_cache)} entries")
                    yield ("", [], "\n\n".join(status))
                    
                    query_level_summaries.extend(followup_query_summaries)
                    source_index = self._merge_dedupe(source_index, hits2)
                    status.append(f"✅ Wave {iteration}: Found {len(source_index)} total unique sources")
                    yield ("", [], "\n\n".join(status))
                    
                    # Summarize only new sources (those with IDs greater than max_id_before)
                    new_sources = [s for s in source_index.values() if s.id > max_id_before]
                    if new_sources:
                        status.append(f"📝 Summarizing {len(new_sources)} new results...")
                        yield ("", [], "\n\n".join(status))
                        new_summaries = await self._summarize_each_source(new_sources)
                        all_summaries.extend(new_summaries)
                        status.append(f"✅ Summarized {len(new_summaries)} new results")
                        yield ("", [], "\n\n".join(status))
                
                # SYNTHESIS: Format findings and write report
                status.append("✍️ Writing research report...")
                yield ("", [], "\n\n".join(status))
                
                # Generate report
                report = await self._write_report(
                    query, source_index, all_summaries, query_level_summaries
                )
                status.append(f"✅ Generated report with {len(report.sections)} sections")
                id_to_source = {item.id: item for item in sorted(source_index.values(), key=lambda x: x.id)}
                md = render_markdown(report, source_index=id_to_source)
                yield (md, [], "\n\n".join(status))
                
                # Build sources_data for final yield
                sources_data = []
                for item in sorted(source_index.values(), key=lambda x: x.id):
                    # Safely truncate title (handle None/empty)
                    title = item.title or ""
                    if len(title) > 80:
                        title = title[:80] + "..."
                    source_type = "news" if item.domain and any(k in item.domain for k in ["news", "cnn", "bbc", "reuters"]) else "web"
                    sources_data.append([title, item.url, source_type, item.date or "N/A"])
                
                status.append("✅ Complete!")
                # Final yield with sources_data
                yield (md, sources_data, "\n\n".join(status))
        
        except Exception as e:
            emsg = str(e)
            error_type = type(e).__name__
            
            if "Connection error" in emsg or "APIConnectionError" in error_type:
                yield ("", [], f"❌ Connection Error: check internet/API key.\n\nDetails: {emsg}")
            elif "Event loop" in emsg or "no current event loop" in emsg:
                yield ("", [], f"❌ Event Loop Error: internal async issue.\n\nDetails: {emsg}")
            else:
                yield ("", [], f"❌ Error ({error_type}): {emsg}")
    
    def _norm_query(self, q: str) -> str:
        """Lowercase, collapse spaces, cap length for safe cache keys."""
        return " ".join((q or "").lower().split())[:300]
    
    async def _web_search_one(self, q: str):
        """Run a single web search under concurrency guard."""
        web_search_async = get_search_provider_async(self.provider, debug=False)
        async with self._search_sem:
            return await web_search_async(q)
    
    async def _web_search_many(self, queries: List[str]) -> Tuple[List[Dict], List[str]]:
        """
        Perform multiple web searches using OpenAI WebSearchTool with caching and concurrency guardrails.
        Returns (list of raw result dicts, list of query-level summaries).
        """
        import asyncio
        
        all_hits: List[Dict] = []
        query_summaries: List[str] = []
        
        async def fetch_or_cache(q: str):
            key = self._norm_query(q)
            # L1: in-memory
            if key in self._search_cache:
                self._cache_hits += 1
                results, summary = self._search_cache[key]
                return summary, results
            
            # L2: disk
            l2 = _cache_get_disk(self._disk_cache_conn, key)
            if l2 is not None:
                self._cache_hits += 1
                results = l2.get("results", [])
                summary = l2.get("summary")
                # populate L1
                self._search_cache[key] = (results, summary)
                return summary, results
            
            # MISS: fetch
            self._cache_misses += 1
            try:
                out = await self._web_search_one(q)
                if isinstance(out, tuple) and len(out) == 2:
                    summary, results = out
                else:
                    summary, results = None, out
            except Exception:
                summary, results = None, []
            
            results = results or []
            # write-through: L1 + L2
            self._search_cache[key] = (results, summary)
            _cache_set_disk(self._disk_cache_conn, key, {"results": results, "summary": summary})
            return summary, results
        
        tasks = [fetch_or_cache(q) for q in queries]
        for coro in asyncio.as_completed(tasks):
            summary, results = await coro
            if summary and summary.strip():
                query_summaries.append(summary.strip())
            
            # Normalize and cap per-query results
            for result in (results or [])[:TOPK_PER_QUERY]:
                if isinstance(result, dict):
                    all_hits.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "snippet": result.get("snippet", ""),
                        "published": result.get("published"),
                        "provider": result.get("provider", "openai"),
                    })
        
        return (all_hits, query_summaries)
    
    def _canon(self, url: str) -> str:
        """Normalize URL for deduplication: lower-case host, strip trailing /, drop #fragment, drop UTM params."""
        try:
            parsed = urlparse(url.strip())
            # Lower-case host
            netloc = parsed.netloc.lower()
            # Strip trailing slash from path
            path = parsed.path.rstrip('/')
            # Drop fragment
            fragment = ''
            # Drop common UTM params
            if parsed.query:
                params = parse_qs(parsed.query, keep_blank_values=True)
                utm_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'fbclid', 'gclid']
                params = {k: v for k, v in params.items() if k not in utm_params}
                query = urlencode(params, doseq=True) if params else ''
            else:
                query = ''
            return urlunparse((parsed.scheme, netloc, path, parsed.params, query, fragment))
        except Exception:
            return url.strip()
    
    def _build_source_index(self, hits: List[Dict], existing_index: Optional[Dict[str, SourceItem]] = None) -> Dict[str, SourceItem]:
        """
        Build or extend Source Index with numeric IDs (1..K).
        Deduplicates by normalized URL. Returns URL -> SourceItem mapping.
        """
        if existing_index is None:
            existing_index = {}
        
        next_id = max([s.id for s in existing_index.values()], default=0) + 1
        
        # Effective cap from UI (defensive min with constant)
        cap = min(self.num_sources, MAX_SOURCES_FINAL)
        
        for hit in hits:
            url = str(hit.get("url", "")).strip()
            if not url:
                continue
            
            # Normalize URL for deduplication
            canon_url = self._canon(url)
            if canon_url in existing_index:
                continue  # Skip duplicates
            
            # Extract domain
            try:
                domain = urlparse(canon_url).netloc.lower()
            except Exception:
                domain = None
            
            source_item = SourceItem(
                id=next_id,
                title=(hit.get("title") or "").strip(),
                url=url,  # Store original URL, but use canon_url for dedupe
                snippet=(hit.get("snippet") or "").strip(),
                date=hit.get("published"),
                domain=domain,
            )
            existing_index[canon_url] = source_item
            next_id += 1
            
            if len(existing_index) >= cap:
                break
        
        return existing_index
    
    def _merge_dedupe(self, existing_index: Dict[str, SourceItem], new_hits: List[Dict]) -> Dict[str, SourceItem]:
        """Merge new hits into existing source index, deduplicating by URL."""
        return self._build_source_index(new_hits, existing_index)
    
    async def _summarize_each_source(self, source_items: List[SourceItem]) -> List[SearchResult]:
        """
        Summarize each source using SearchAgent with bounded concurrency.
        Preserves ordering by index.
        """
        import asyncio
        summarizer = SearchAgent(openai_client=self.openai_client)
        
        async def summarize_guarded(i: int, item: SourceItem):
            try:
                async with self._summary_sem:
                    s = await summarizer.summarize_result_async(item)
                return (i, s or "")
            except Exception:
                return (i, "")
        
        tasks = [summarize_guarded(i, it) for i, it in enumerate(source_items)]
        results_by_idx = [""] * len(source_items)
        
        for coro in asyncio.as_completed(tasks):
            i, summary = await coro
            results_by_idx[i] = summary
        
        out: List[SearchResult] = []
        for it, summary in zip(source_items, results_by_idx):
            out.append(SearchResult(
                id=it.id,
                title=it.title,
                url=it.url,
                summary=summary or it.snippet  # Fallback on snippet
            ))
        return out
    
    def _join_findings(self, query: str, source_index: Dict[str, SourceItem], summaries: List[SearchResult]) -> str:
        """
        Build findings text for follow-up decision agent.
        Includes top 10 summaries and a section describing what has NOT been found yet.
        """
        text = f"Query: {query}\n\n"
        
        # Top 10 summaries (ID, Title, Summary)
        text += "Top 10 Summaries:\n"
        sorted_summaries = sorted(summaries, key=lambda x: x.id)[:10]
        for result in sorted_summaries:
            text += f"\n{result.id}. Title: {result.title}\n   Summary: {result.summary}\n"
        
        # Section describing what has NOT been found yet (empty sections)
        text += "\n\nWhat Has NOT Been Found Yet:\n"
        text += "- Missing data or statistics\n"
        text += "- Conflicting sources or viewpoints\n"
        text += "- Unexplored angles or perspectives\n"
        text += "- Case studies or real-world examples\n"
        text += "- Technical depth or detailed explanations\n"
        text += "- Trends or future implications\n"
        text += "- Expert opinions or authoritative sources\n"
        text += "- Historical context or evolution\n"
        text += "- Comparisons with alternatives\n"
        text += "- Risks, limitations, or controversies\n"
        text += "\n(Note: The above list represents potential gaps. Evaluate which of these are actually missing based on the summaries above.)\n"
        
        return text
    
    async def _write_report(self, query: str, source_index: Dict[str, SourceItem], summaries: List[SearchResult], query_level_summaries: List[str]) -> ResearchReport:
        """
        Write the research report using WriterAgent.
        Formats findings in the reference style and passes to Writer.
        Post-processes report to ensure citations match Source Index.
        """
        from app.core.retry import with_retry
        import re
        
        # Reconstruct SourceDoc list from source_index for WriterAgent
        source_items = sorted(source_index.values(), key=lambda x: x.id)
        sources: List[SourceDoc] = []
        # Create ID -> SourceItem mapping for citation validation
        id_to_source: Dict[int, SourceItem] = {item.id: item for item in source_items}
        
        for item in source_items:
            try:
                sources.append(SourceDoc(
                    title=item.title,
                    url=item.url,  # Let Pydantic validate HttpUrl on model creation
                    snippet=item.snippet,
                    published=item.date,
                    source_type="news" if item.domain and any(k in item.domain for k in ["news", "cnn", "bbc", "reuters"]) else "web",
                    provider="openai",
                ))
            except Exception:
                continue
        
        # Format summaries in reference style: "1. Title: ...\n   URL: ...\n   Summary: ..."
        # This matches the format expected by the reference synthesis_agent
        formatted_summaries: List[str] = []
        
        # Include query-level summaries first (provide high-level context)
        if query_level_summaries:
            formatted_summaries.append("Query-level search summaries:\n" + "\n\n".join(query_level_summaries) + "\n")
        
        # Then include per-result summaries with IDs
        for result in summaries:
            formatted_summaries.append(f"{result.id}. Title: {result.title}\n   URL: {result.url}\n   Summary: {result.summary}")
        
        writer = WriterAgent(openai_client=self.openai_client)
        report = await with_retry(lambda: writer.draft_async(
            topic=query,
            subtopics=[],  # No subtopics in new flow
            summaries=formatted_summaries,  # Query-level + per-result summaries
            sources=sources,
        ))
        
        # Post-process: Extract numeric citations from text and validate against Source Index
        from app.schemas.report import Section
        processed_sections: List[Section] = []
        for sec in report.sections:
            # Extract numeric citations like [1], [2], [10] from the text
            citation_ids = set()
            pattern = r'\[(\d+)\]'
            matches = re.findall(pattern, sec.summary)
            for match in matches:
                try:
                    citation_id = int(match)
                    # Only keep citations that exist in Source Index
                    if citation_id in id_to_source:
                        citation_ids.add(citation_id)
                except ValueError:
                    continue
            
            # Store IDs directly in citations
            processed_sections.append(Section(
                title=sec.title,
                summary=sec.summary,  # Text already has [1], [2] citations
                citations=sorted(citation_ids),  # Store IDs directly
            ))
        
        # Return report with processed sections
        report.sections = processed_sections
        
        return report
    
