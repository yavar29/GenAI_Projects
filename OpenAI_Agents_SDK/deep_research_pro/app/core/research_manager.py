"""
ResearchManager: Orchestrates the entire Deep Research pipeline.

This module contains the main ResearchManager class that coordinates all agents and manages
the complete research workflow from user query to final report.

Pipeline Overview:
1. Planning: QueryGeneratorAgent creates diverse search queries
2. File Processing (optional): FileSummarizerAgent processes uploaded documents in parallel
3. Research Waves: Iterative web search with parallel processing
   - Each wave: parallel queries → parallel result summarization → deduplication
   - FollowUpDecisionAgent determines if more waves needed
4. Report Generation: WriterAgent synthesizes sources into structured report
   - Source filtering and deduplication
   - Subtopic theme extraction
   - Cross-source synthesis
   - Output validation and retry logic

Key Features:
- Parallel processing for file chunks, queries, and result summarization
- Two-level caching (L1: in-memory, L2: SQLite) with TTL and LRU
- Multi-wave research with intelligent follow-up queries
- Structured output validation with automatic retry
- Analytics tracking for efficiency metrics
"""

import os
import asyncio
import traceback
import time

import re
from typing import Dict, List, AsyncGenerator, Optional, Tuple
from pathlib import Path

from openai import AsyncOpenAI
from agents import trace, gen_trace_id

from app.agents.planner_agent import QueryGeneratorAgent, FollowUpDecisionAgent
from app.agents.search_agent import SearchAgent
from app.agents.writer_agent import WriterAgent
from app.agents.file_summarizer_agent import FileSummarizerAgent

from app.schemas.source import SourceDoc, SourceItem
from app.schemas.plan import QueryResponse, FollowUpDecisionResponse
from app.schemas.report import ResearchReport
from app.core.settings import (
    MAX_UPLOAD_FILES,
    SUPPORTED_FILE_TYPES,
    UPLOAD_DIR,
    OPENAI_API_KEY,
)
from app.core.tracing import TRACE_DASHBOARD
from app.core.openai_client import make_async_client
from app.tools.hosted_tools import get_search_provider_async
from app.core.render import render_markdown
from app.schemas.analytics import EfficiencyMetrics, WaveStat
from app.core.analytics_builder import build_analytics_payload
from app.core.cache_manager import get_cache_manager

# Configuration constants
MAX_WAVES = 3
TOPK_PER_QUERY = 5
MAX_SOURCES_FINAL = 25

class ResearchManager:
    """Orchestrates research pipeline: planning, search, file processing, follow-up, writing."""

    def __init__(
        self,
        client: Optional[AsyncOpenAI] = None,
        max_sources: int = 25,
        max_waves: int = 2,
        topk_per_query: int = 5,
        num_searches: int = 5,  # For backward compatibility
        num_sources: int = 8,  # For backward compatibility
    ):
        self.client = client or make_async_client()
        self.max_sources = max_sources
        self.max_waves = max_waves
        self.topk = topk_per_query
        self.num_searches = num_searches
        self.num_sources = num_sources

        # Ensure API key is in environment for Agents SDK
        if OPENAI_API_KEY and not hasattr(self, '_api_key_set'):
            os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
            self._api_key_set = True

        # Agents
        self.planner = QueryGeneratorAgent(openai_client=self.client)
        self.search_agent = SearchAgent(openai_client=self.client)
        self.followup_agent = FollowUpDecisionAgent(openai_client=self.client)
        self.writer = WriterAgent(openai_client=self.client)
        self.file_agent = FileSummarizerAgent(self.client)

        # Caches
        self.cache_manager = get_cache_manager()
        self.source_index: Dict[str, SourceDoc] = {}

        # Metrics for efficiency / analytics
        self.metrics_queries_executed = 0
        self.metrics_total_sources_seen = 0
        self.metrics_cache_hits = 0
        self.metrics_cache_misses = 0

        # Ensure upload directory exists
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        # Get search provider
        self.web_search_async = get_search_provider_async("hosted")

    # -----------------------------------------------------------
    # UTILITIES
    # -----------------------------------------------------------

    def _norm_query(self, q: str) -> str:
        """Normalize queries for caching."""
        return q.lower().strip()
    
    def _normalize_url(self, url: str) -> str:
        """Normalize and fix malformed URLs.
        
        Fixes common URL issues:
        - Removes angle brackets
        - Adds https:// if protocol missing
        - Handles relative URLs
        """
        if not url:
            return ""
        
        # Remove angle brackets
        url = url.strip('<>').strip()
        
        # If already a valid URL, return as-is
        if url.startswith(('http://', 'https://')):
            return url
        
        # If relative URL, return as-is (will be handled in render)
        if url.startswith('/'):
            return url
        
        # If looks like a domain (has dot and reasonable length), add https
        if '.' in url and len(url) > 4 and not url.startswith('<'):
            return f"https://{url}"
        
        # Otherwise return as-is (will be marked as invalid in render)
        return url

    def _merge_sources(self, new_sources: List[SourceDoc]):
        """Merge sources into global index."""
        for src in new_sources:
            if src.url not in self.source_index:
                self.source_index[src.url] = src
    
    def _deduplicate_sources(self, sources: List[SourceDoc]) -> List[SourceDoc]:
        """Remove duplicate sources based on content similarity."""
        seen_content = set()
        filtered = []
        for src in sources:
            content = (src.content or src.snippet or "").strip()
            if not content:
                continue
            # Use a hash of first 500 chars to detect near-duplicates
            content_key = content[:500].lower()
            if content_key not in seen_content:
                seen_content.add(content_key)
                filtered.append(src)
        return filtered
    
    def _filter_top_sources(self, sources: List[SourceDoc], top_k: int = 15) -> List[SourceDoc]:
        """Filter to top K unique sources, prioritizing those with richer content."""
        unique_sources = self._deduplicate_sources(sources)
        # Sort by content length (richer sources first), then take top K
        sorted_sources = sorted(
            unique_sources,
            key=lambda s: len(s.content or s.snippet or ""),
            reverse=True
        )
        return sorted_sources[:top_k]
    
    def _estimate_token_count(self, text: str) -> int:
        """Estimate token count (rough approximation: ~4 chars per token for English)."""
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model("gpt-4o")
            return len(encoding.encode(text))
        except ImportError:
            # Fallback: rough estimate (4 chars per token)
            return len(text) // 4
    
    def _extract_subtopics_from_topic(self, topic: str) -> List[str]:
        """Extract subtopics from topic string when it enumerates multiple topics.
        
        Handles cases like:
        - "Mars colonization, new propulsion systems, search for extraterrestrial life"
        - "AI in healthcare: diagnostics, treatment, and ethics"
        - "Future of space exploration: Focus on topics like X, Y, or Z"
        
        Args:
            topic: The original research topic string
        
        Returns:
            List of extracted subtopic strings, or empty list if none found
        """
        if not topic:
            return []
        
        # Common separators that indicate multiple subtopics
        separators = [",", ";", ":", "|", "or", "and"]
        
        # Look for patterns like "Focus on topics like X, Y, or Z"
        focus_pattern = r"(?:focus on|topics? like|including|such as|e\.g\.|for example)[:\s]+(.+)"
        match = re.search(focus_pattern, topic, re.IGNORECASE)
        if match:
            topic_part = match.group(1)
            # Split by common separators
            for sep in separators:
                if sep in topic_part:
                    parts = [p.strip() for p in topic_part.split(sep) if p.strip()]
                    if len(parts) >= 2:
                        # Clean up each part (remove leading articles, etc.)
                        cleaned = []
                        for p in parts:
                            p = p.strip()
                            # Remove leading "the", "a", "an" if present
                            p = re.sub(r'^(the|a|an)\s+', '', p, flags=re.IGNORECASE)
                            if len(p) > 10:  # Only keep substantial subtopics
                                cleaned.append(p)
                        if cleaned:
                            return cleaned[:7]  # Max 7 subtopics
        
        # Try splitting by comma if topic contains multiple parts
        if "," in topic:
            parts = [p.strip() for p in topic.split(",") if p.strip()]
            if len(parts) >= 2:
                # Check if parts look like subtopics (not just a list of words)
                cleaned = []
                for p in parts:
                    p = p.strip()
                    # Skip if it's too short or looks like a single word
                    if len(p) > 15 and " " in p:
                        cleaned.append(p)
                if len(cleaned) >= 2:
                    return cleaned[:7]
        
        return []

    def _extract_subtopic_themes(self, queries: List[str], topic: str = "") -> List[str]:
        """Extract meaningful subtopic themes from queries for better report structure.
        
        Analyzes query text to identify common research angles and converts them into
        structured theme names that guide the WriterAgent's report organization.
        
        Detected themes include:
        - Background & Fundamentals
        - Statistics & Data
        - Future Trends & Outlook
        - Case Studies & Examples
        - Risks & Challenges
        - Limitations & Constraints
        - Comparisons & Alternatives
        - Adoption & Implementation
        - Benefits & Advantages
        
        Args:
            queries: List of search query strings
            topic: Original research topic (used as fallback if queries are empty/generic)
        
        Returns:
            List of theme names (top 5-7) sorted by frequency in queries
        
        Falls back to extracting from topic or query snippets if no themes are detected.
        """
        if not queries:
            # If no queries, try extracting from topic itself
            if topic:
                topic_subtopics = self._extract_subtopics_from_topic(topic)
                if topic_subtopics:
                    return topic_subtopics
            return []
        
        # Common theme keywords
        theme_keywords = {
            "background": ["background", "definition", "what is", "overview", "introduction", "basics", "fundamentals"],
            "statistics": ["statistics", "data", "numbers", "percentage", "rate", "survey", "study", "research"],
            "trends": ["trend", "future", "forecast", "prediction", "outlook", "emerging", "upcoming"],
            "case_studies": ["case study", "example", "instance", "use case", "real-world", "implementation"],
            "risks": ["risk", "danger", "threat", "challenge", "problem", "issue", "concern"],
            "limitations": ["limitation", "drawback", "disadvantage", "weakness", "constraint"],
            "comparison": ["compare", "versus", "vs", "difference", "alternative", "vs", "versus"],
            "adoption": ["adoption", "implementation", "deployment", "usage", "adoption rate"],
            "benefits": ["benefit", "advantage", "pro", "strength", "positive"],
        }
        
        # Count theme matches per query
        theme_counts = {theme: 0 for theme in theme_keywords.keys()}
        
        for query_lower in [q.lower() for q in queries]:
            for theme, keywords in theme_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    theme_counts[theme] += 1
        
        # Convert to readable subtopic names
        theme_names = {
            "background": "Background & Fundamentals",
            "statistics": "Statistics & Data",
            "trends": "Future Trends & Outlook",
            "case_studies": "Case Studies & Examples",
            "risks": "Risks & Challenges",
            "limitations": "Limitations & Constraints",
            "comparison": "Comparisons & Alternatives",
            "adoption": "Adoption & Implementation",
            "benefits": "Benefits & Advantages",
        }
        
        # Get top themes (at least 2 matches or top 5)
        sorted_themes = sorted(
            [(theme, count) for theme, count in theme_counts.items() if count > 0],
            key=lambda x: x[1],
            reverse=True
        )
        
        # Return top 5-7 themes as subtopics
        subtopics = [theme_names[theme] for theme, _ in sorted_themes[:7]]
        
        # If we don't have enough themes, use first few queries as fallback
        if len(subtopics) < 3:
            subtopics.extend([q[:60] for q in queries[:5] if q not in subtopics])
            subtopics = subtopics[:7]
        
        return subtopics

    # -----------------------------------------------------------
    # FILE HANDLING
    # -----------------------------------------------------------

    async def process_uploaded_files(
        self, filepaths: List[str], status_messages: List[str]
    ) -> List[SourceDoc]:
        """Process uploaded files in parallel: extract, chunk, summarize, merge.
        
        Handles PDF, DOCX, and TXT files. Each file is processed independently in parallel:
        1. Text extraction (format-specific)
        2. Semantic chunking (LLM-based section detection)
        3. Parallel chunk summarization (all chunks processed concurrently)
        4. Summary merging into single SourceDoc per file
        
        Args:
            filepaths: List of file paths to process
            status_messages: List to append status updates (modified in-place)
        
        Returns:
            List of SourceDoc objects, one per successfully processed file
        
        Files with unsupported types or processing errors are skipped with error messages
        added to status_messages.
        """
        if not filepaths:
            return []

        # Filter valid files first
        valid_files = []
        for fp in filepaths:
            fname = os.path.basename(fp)
            ext = os.path.splitext(fname)[1].lower()
            if ext not in SUPPORTED_FILE_TYPES:
                status_messages.append(f"❌ Unsupported file type: {fname}")
                continue
            valid_files.append(fp)
            status_messages.append(f"📄 Processing file: {fname} (Semantic Chunking)")

        if not valid_files:
            return []

        # Process all files in parallel
        async def process_single_file(fp: str) -> Optional[SourceDoc]:
            fname = os.path.basename(fp)
            try:
                summary_doc = await self.file_agent.process_file(fp)
                status_messages.append(f"✅ Completed: {fname}")
                return summary_doc
            except Exception as e:
                status_messages.append(f"❌ Error processing {fname}: {e}")
                traceback.print_exc()
                return None

        # Launch all file processing tasks in parallel
        file_tasks = [process_single_file(fp) for fp in valid_files]
        results = await asyncio.gather(*file_tasks, return_exceptions=True)
        
        # Filter out None and exceptions
        summaries = []
        for result in results:
            if isinstance(result, Exception):
                continue
            if result is not None:
                summaries.append(result)

        return summaries

    # -----------------------------------------------------------
    # WEB SEARCH + SUMMARIZATION
    # -----------------------------------------------------------

    async def _summarize_sources(
        self, source_items: List[Tuple[SourceItem, Dict]]
    ) -> List[SourceDoc]:
        """Helper: Summarize a list of source items in parallel and return SourceDoc objects."""
        if not source_items:
            return []
        
        tasks = [self.search_agent.summarize_result_async(item[0]) for item in source_items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        summarized = []
        for (item, raw), summary in zip(source_items, results):
            if isinstance(summary, Exception):
                print(f"Warning: Failed to summarize result {item.title}: {summary}")
                content = item.snippet or ""
            else:
                content = summary if summary else (item.snippet or "")
            
            # Normalize URL before creating SourceDoc
            normalized_url = self._normalize_url(item.url)
            
            summarized.append(SourceDoc(
                title=item.title,
                url=normalized_url,
                snippet=content[:350] if content else "",
                content=content,
                published=item.date,
                source_type=raw.get("source_type", "web"),
                provider=raw.get("provider", "openai"),
            ))
        
        return summarized

    async def run_web_search(
        self, queries: List[str], status_messages: List[str]
    ) -> Tuple[List[SourceDoc], List[str]]:
        """Execute search pipeline: cache lookup, web search, summarization, deduplication.
        
        Processes all queries in parallel for maximum speed. For each query:
        1. Check two-level cache (L1: in-memory, L2: SQLite)
        2. If cache miss: Execute web search via WebSearchTool
        3. Parallel summarization of all results for the query
        4. Convert to SourceDoc objects with full summaries
        
        Args:
            queries: List of search query strings to execute
            status_messages: List to append status updates (modified in-place)
        
        Returns:
            Tuple of (sources, query_summaries):
            - sources: List of SourceDoc objects (deduplicated by URL)
            - query_summaries: List of query-level summary strings for report context
        
        All queries are processed concurrently, and result summarization within each query
        is also parallelized for optimal performance.
        """
        unique_sources = []
        query_summaries = []

        async def process_single_query(q: str) -> Tuple[List[SourceDoc], Optional[str]]:
            """Process a single query and return (sources, query_summary)."""
            nq = self._norm_query(q)
            status_messages.append(f"🔍 Searching: {q}")

            self.metrics_queries_executed += 1
            query_summary = None

            # Check cache (L1 + L2)
            cached = self.cache_manager.get(nq)
            if cached:
                self.metrics_cache_hits += 1
                status_messages.append(f"↪ Cache hit for query: {q}")
                cached_results, cached_summary = cached
                # Store query-level summary if available
                if cached_summary:
                    query_summary = f"Query: {q}\nSummary: {cached_summary}"
                # Convert cached dicts to SourceItem tuples for summarization
                # For cached results, we need to re-summarize to get full detailed summaries
                results_to_process = cached_results[:self.topk]
                
                source_items = []
                for r in results_to_process:
                    source_item = SourceItem(
                        id=0,
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        snippet=r.get("snippet", ""),
                        date=r.get("published"),
                    )
                    source_items.append((source_item, r))
                
                try:
                    query_sources = await self._summarize_sources(source_items)
                    self.metrics_total_sources_seen += len(query_sources)
                    return query_sources, query_summary
                except Exception as e:
                    status_messages.append(f"⚠️ Error during parallel summarization for cached results: {e}")
                    return [], query_summary
            else:
                self.metrics_cache_misses += 1
                # Perform web search
                try:
                    summary, web_results = await self.web_search_async(q)
                    # Store query-level summary
                    if summary:
                        query_summary = f"Query: {q}\nSummary: {summary}"
                    # Store in cache (L1 + L2)
                    self.cache_manager.set(nq, web_results, summary)
                    
                    # Limit to topk
                    web_results = web_results[:self.topk]
                    
                    # Prepare source items for summarization
                    source_items = []
                    for r in web_results:
                        source_item = SourceItem(
                            id=0,
                            title=r.get("title", ""),
                            url=r.get("url", ""),
                            snippet=r.get("snippet", ""),
                            date=r.get("published"),
                        )
                        source_items.append((source_item, r))
                    
                    try:
                        query_sources = await self._summarize_sources(source_items)
                        self.metrics_total_sources_seen += len(query_sources)
                        return query_sources, query_summary
                    except Exception as e:
                        status_messages.append(f"⚠️ Error during parallel summarization: {e}")
                        return [], query_summary
                except Exception as e:
                    status_messages.append(f"❌ Error searching {q}: {e}")
                    return [], None

        # Process all queries in parallel
        query_tasks = [process_single_query(q) for q in queries]
        query_results = await asyncio.gather(*query_tasks, return_exceptions=True)
        
        # Collect results
        for result in query_results:
            if isinstance(result, Exception):
                continue
            query_sources, q_summary = result
            unique_sources.extend(query_sources)
            if q_summary:
                query_summaries.append(q_summary)

        # Deduplicate
        final_sources = []
        seen_urls = set()

        for src in unique_sources:
            if src.url not in seen_urls:
                final_sources.append(src)
                seen_urls.add(src.url)

        return final_sources, query_summaries

    # -----------------------------------------------------------
    # MAIN RESEARCH PIPELINE
    # -----------------------------------------------------------

    async def run(
        self,
        topic: str,
        queries: Optional[List[str]] = None,
        uploaded_files: Optional[List[str]] = None,
        approved_queries: Optional[List[str]] = None,  # For backward compatibility
    ) -> AsyncGenerator[Tuple[str, List, str, Optional[object]], None]:
        """Execute multi-wave research pipeline. Yields (report_md, sources_data, status_text, analytics)."""
        if approved_queries:
            queries = approved_queries

        # Generate queries if not provided
        if not queries:
            query_response = await self.planner.generate_async(topic)
            queries = query_response.queries[:self.num_searches]

        status_messages = []

        # ----------- INITIALIZATION ----------
        start_time = time.monotonic()
        wave = 1
        waves_total = min(self.max_waves, self.max_waves)
        final_report = None

        # Reset metrics for this run
        self.metrics_queries_executed = 0
        self.metrics_total_sources_seen = 0
        self.metrics_cache_hits = 0
        self.metrics_cache_misses = 0
        
        # Track wave statistics
        wave_stats_list: List[WaveStat] = []
        
        # Track all queries and query-level summaries across waves
        all_queries_used: List[str] = []
        all_query_summaries: List[str] = []

        # Generate trace ID
        trace_id = gen_trace_id()
        trace_url = f"{TRACE_DASHBOARD}{trace_id}"
        status_messages.append(f"🔗 Trace: {trace_url}")

        yield ("", [], "\n\n".join(status_messages), None)

        with trace("Research trace", trace_id=trace_id):
            # ----------- FILE SUMMARIES (WAVE 0) ----------
            if uploaded_files:
                status_messages.append(f"📂 Found {len(uploaded_files)} user-uploaded file(s).")
                yield ("", [], "\n\n".join(status_messages), None)

                files_summaries = await self.process_uploaded_files(
                    uploaded_files, status_messages
                )
                self._merge_sources(files_summaries)
                status_messages.append("📁 File processing completed.\n")
                yield ("", [], "\n\n".join(status_messages), None)

            # ----------- MULTI-WAVE SEARCH ----------
            while wave <= waves_total:
                wave_start_time = time.monotonic()
                status_messages.append(f"🌊 Starting Wave {wave}/{waves_total}")
                yield ("", [], "\n\n".join(status_messages), None)

                # Track queries for this wave
                wave_queries_count = len(queries)
                all_queries_used.extend(queries)
                
                # Step 1 — Web search
                wave_sources, wave_query_summaries = await self.run_web_search(
                    queries, status_messages
                )
                
                # Collect query-level summaries
                all_query_summaries.extend(wave_query_summaries)
                
                # Track sources discovered in this wave
                wave_sources_count = len(wave_sources)

                # Merge
                self._merge_sources(wave_sources)
                
                # Calculate wave duration
                wave_duration = time.monotonic() - wave_start_time

                status_messages.append(f"🧮 Total unique sources so far: {len(self.source_index)}")
                yield ("", [], "\n\n".join(status_messages), None)
                
                # Record wave statistics
                wave_stats_list.append(
                    WaveStat(
                        wave_index=wave,
                        num_queries=wave_queries_count,
                        num_sources_discovered=wave_sources_count,
                        duration_seconds=wave_duration,
                    )
                )

                # Step 2 — Follow-Up Decision
                # Build findings text for follow-up decision
                findings_text = f"Topic: {topic}\n\nSources found: {len(self.source_index)}\n"
                for i, src in enumerate(list(self.source_index.values())[:10], 1):
                    findings_text += f"{i}. {src.title} - {src.snippet[:100]}...\n"

                followup = await self.followup_agent.decide_async(
                    original_query=topic,
                    findings_text=findings_text,
                )

                if not followup.should_follow_up or wave == waves_total:
                    status_messages.append(f"✔ No more follow-ups required. Ending search waves.\n")
                    yield ("", [], "\n\n".join(status_messages), None)
                    break

                queries = followup.queries[:self.num_searches]
                wave += 1
                status_messages.append(f"🔄 Follow-up queries generated ({len(queries)})")
                yield ("", [], "\n\n".join(status_messages), None)

            # ----------- FINAL WRITING ----------
            status_messages.append("✍️ Writing final long-form report...")
            yield ("", [], "\n\n".join(status_messages), None)

            all_sources_list = list(self.source_index.values())[:self.max_sources]
            
            # Filter and deduplicate sources before writing
            filtered_sources = self._filter_top_sources(all_sources_list, top_k=15)
            status_messages.append(f"📝 Filtered to {len(filtered_sources)} unique sources (from {len(all_sources_list)})")

            # Format sources for writer - truncate long summaries and enhance titles
            summaries = []
            for src in filtered_sources:
                # Use content (full detailed summary) if available, fallback to snippet
                summary_text = src.content if src.content else (src.snippet or "")
                # Truncate very long summaries (keep first 3000 chars + key points)
                if len(summary_text) > 3000:
                    # Try to preserve structure by keeping first part and last 200 chars
                    summary_text = summary_text[:2800] + "... [truncated] ..." + summary_text[-200:]
                
                # Enhance title with context for better synthesis
                title = src.title or "Untitled Source"
                if len(title) < 40 and summary_text:
                    # Extract key topic from summary for context
                    summary_words = summary_text.split()[:8]
                    if summary_words:
                        topic_hint = " ".join(summary_words)
                        title = f"{title} – {topic_hint[:50]}"
                
                summaries.append(f"Title: {title}\nURL: {src.url}\nSummary: {summary_text}")

            # Extract meaningful subtopic themes from queries for better report structure
            subtopic_themes = self._extract_subtopic_themes(all_queries_used, topic=topic)
            if not subtopic_themes:
                # Fallback 1: Try extracting from topic itself if it enumerates subtopics
                topic_subtopics = self._extract_subtopics_from_topic(topic)
                if topic_subtopics:
                    subtopic_themes = topic_subtopics
                else:
                    # Fallback 2: use first few queries as subtopics
                    if all_queries_used:
                        subtopic_themes = [q[:60] for q in all_queries_used[:7]]
                    else:
                        # Final fallback: use topic as single subtopic
                        subtopic_themes = [topic[:60]]
            
            status_messages.append(f"📋 Report structure themes: {', '.join(subtopic_themes[:5])}")
            
            # Prepare query-level summaries for prompt (truncate if too long)
            query_level_summaries_text = ""
            if all_query_summaries:
                query_level_summaries_text = "\n\n".join(all_query_summaries)
                # Limit query summaries to reasonable length
                if len(query_level_summaries_text) > 2000:
                    query_level_summaries_text = query_level_summaries_text[:1800] + "... [truncated]"

            # Estimate token count for final prompt and log if needed
            prompt_parts = [
                topic,
                " ".join(subtopic_themes),
                query_level_summaries_text,
                "\n".join(summaries),
            ]
            estimated_prompt_tokens = self._estimate_token_count("\n\n".join(prompt_parts))
            if estimated_prompt_tokens > 10000:
                status_messages.append(
                    f"⚠️ Writer prompt is long (~{estimated_prompt_tokens} tokens). "
                    f"Consider further filtering sources if needed."
                )

            # Call writer with filtered sources and meaningful subtopics
            final_report = await self.writer.draft_async(
                topic=topic,
                subtopics=subtopic_themes,
                summaries=summaries,
                sources=filtered_sources,
                query_level_summaries=query_level_summaries_text,
            )
            
            # Enhanced validation of structured output
            validation_issues = []
            if not final_report.sections:
                validation_issues.append("missing sections")
            else:
                # Check for quality issues
                empty_sections = [i for i, sec in enumerate(final_report.sections) if not sec.summary or len(sec.summary.strip()) < 50]
                if empty_sections:
                    validation_issues.append(f"empty/too-short sections: {empty_sections}")
                
                generic_titles = [i for i, sec in enumerate(final_report.sections) if sec.title and len(sec.title) < 10]
                if generic_titles:
                    validation_issues.append(f"generic section titles: {generic_titles}")
                
                # Check if sections have meaningful content
                total_content_length = sum(len(sec.summary or "") for sec in final_report.sections)
                if total_content_length < 500:
                    validation_issues.append(f"insufficient content (total: {total_content_length} chars)")
            
            if validation_issues:
                status_messages.append(
                    f"⚠️ Writer output validation issues: {', '.join(validation_issues)}. "
                    f"Retrying with simplified prompt..."
                )
                # Fallback: retry with simplified approach
                simplified_sources = filtered_sources[:10]
                simplified_summaries = summaries[:10]
                final_report = await self.writer.draft_async(
                    topic=topic,
                    subtopics=subtopic_themes[:5],  # Use fewer subtopics
                    summaries=simplified_summaries,  # Use fewer summaries
                    sources=simplified_sources,  # Use fewer sources
                    query_level_summaries=query_level_summaries_text[:1000] if query_level_summaries_text else "",
                )
                
                # Re-validate after retry
                if not final_report.sections:
                    raise ValueError("WriterAgent failed to generate sections after retry. Check prompt and model configuration.")
                
                # Log retry success
                status_messages.append("✅ Retry successful - report generated with simplified prompt.")
            else:
                status_messages.append(f"✅ Report generated successfully with {len(final_report.sections)} sections.")

            # Render markdown
            # Build source index for citations (use filtered sources for final report)
            id_to_source = {i+1: src for i, src in enumerate(filtered_sources)}
            md = render_markdown(final_report, source_index=id_to_source)

            status_messages.append("📄 Report complete.\n")

            # Calculate total duration
            total_duration = time.monotonic() - start_time

            # Build efficiency metrics
            total_queries = self.metrics_queries_executed
            total_seen = self.metrics_total_sources_seen
            unique_used = len(filtered_sources)

            total_cache_ops = self.metrics_cache_hits + self.metrics_cache_misses
            cache_hit_rate = (
                self.metrics_cache_hits / total_cache_ops if total_cache_ops > 0 else None
            )

            efficiency = EfficiencyMetrics(
                queries_executed=total_queries,
                total_sources_seen=total_seen,
                unique_sources_used=unique_used,
                cache_hit_rate=cache_hit_rate,
                waves_completed=wave,
                total_duration_seconds=total_duration,
            )

            # Build analytics payload (use filtered sources for final report)
            analytics = build_analytics_payload(
                topic=topic,
                report=final_report,
                sources=filtered_sources,
                wave_stats=wave_stats_list,
                efficiency=efficiency,
            )

            # Build sources_data for final yield
            sources_data = []
            for i, src in enumerate(filtered_sources, 1):
                title = src.title or ""
                if len(title) > 80:
                    title = title[:80] + "..."
                source_type = src.source_type or "web"
                sources_data.append([title, src.url, source_type, src.published or "N/A"])

            yield (md, sources_data, "\n\n".join(status_messages), analytics)

    # -----------------------------------------------------------
    # PLANNING WRAPPER
    # -----------------------------------------------------------

    async def generate_plan(self, topic: str) -> QueryResponse:
        """Generate initial search plan with queries and thoughts."""
        return await self.planner.generate_async(topic)
