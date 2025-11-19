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
from typing import Dict, List, AsyncGenerator, Optional, Tuple, Set
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

# Rate limiting: Limit concurrent API calls to avoid hitting TPM limits
# With 30K TPM limit, we want to be conservative
MAX_CONCURRENT_SEARCHES = 3  # Process queries in smaller batches
MAX_CONCURRENT_SUMMARIES = 5  # Limit parallel summarization

# Helper functions for cross-wave improvement tracking
def _extract_citations_from_text(text: str) -> set[int]:
    """Extract all citation IDs from text (e.g., [1], [2][3])."""
    citations = set()
    # Match [1], [2], [10], etc.
    matches = re.findall(r'\[(\d+)\]', text)
    for match in matches:
        try:
            citations.add(int(match))
        except ValueError:
            pass
    return citations

def _word_count(text: str) -> int:
    """Count words in text (consistent with analytics_builder._safe_word_count)."""
    if not text:
        return 0
    return len(text.split())

def _calculate_report_quality_score(report: ResearchReport) -> float:
    """
    Calculate a quality score for a report (0.0 to 1.0).
    Factors: word count, section count, citation density, section length.
    """
    if not report.sections:
        return 0.0
    
    total_words = sum(_word_count(sec.summary or "") for sec in report.sections)
    num_sections = len(report.sections)
    all_citations = set()
    for sec in report.sections:
        all_citations.update(sec.citations)
        all_citations.update(_extract_citations_from_text(sec.summary or ""))
    
    num_citations = len(all_citations)
    
    # Normalize factors (heuristic weights)
    word_score = min(total_words / 2000.0, 1.0)  # Target: 2000 words
    section_score = min(num_sections / 8.0, 1.0)  # Target: 8 sections
    citation_score = min(num_citations / 15.0, 1.0)  # Target: 15 unique citations
    
    # Average section length (words per section)
    avg_section_length = total_words / num_sections if num_sections > 0 else 0
    section_length_score = min(avg_section_length / 250.0, 1.0)  # Target: 250 words/section
    
    # Weighted average
    quality = (
        word_score * 0.3 +
        section_score * 0.2 +
        citation_score * 0.3 +
        section_length_score * 0.2
    )
    
    return quality

def _calculate_report_deltas(
    previous_report: Optional[ResearchReport],
    current_report: ResearchReport
) -> Tuple[int, int, int, float]:
    """
    Calculate deltas between two reports.
    
    Returns:
        (text_added, text_rewritten, citations_added, quality_change)
    """
    if previous_report is None:
        # First wave - everything is new
        total_words = sum(_word_count(sec.summary or "") for sec in current_report.sections)
        all_citations = set()
        for sec in current_report.sections:
            all_citations.update(sec.citations)
            all_citations.update(_extract_citations_from_text(sec.summary or ""))
        quality = _calculate_report_quality_score(current_report)
        return total_words, 0, len(all_citations), quality
    
    # Calculate previous metrics
    prev_words = sum(_word_count(sec.summary or "") for sec in previous_report.sections)
    prev_citations = set()
    for sec in previous_report.sections:
        prev_citations.update(sec.citations)
        prev_citations.update(_extract_citations_from_text(sec.summary or ""))
    prev_quality = _calculate_report_quality_score(previous_report)
    
    # Calculate current metrics
    curr_words = sum(_word_count(sec.summary or "") for sec in current_report.sections)
    curr_citations = set()
    for sec in current_report.sections:
        curr_citations.update(sec.citations)
        curr_citations.update(_extract_citations_from_text(sec.summary or ""))
    curr_quality = _calculate_report_quality_score(current_report)
    
    # Calculate deltas
    text_added = max(0, curr_words - prev_words)
    
    # Estimate text rewritten by comparing section titles and content similarity
    # Simple heuristic: if section titles match, assume content was rewritten
    prev_titles = {sec.title for sec in previous_report.sections}
    curr_titles = {sec.title for sec in current_report.sections}
    common_titles = prev_titles & curr_titles
    
    # For common sections, estimate rewritten words as average section length
    rewritten_words = 0
    if common_titles:
        avg_section_length = prev_words / len(previous_report.sections) if previous_report.sections else 0
        rewritten_words = int(len(common_titles) * avg_section_length * 0.5)  # Assume 50% rewritten
    
    citations_added = len(curr_citations - prev_citations)
    quality_change = curr_quality - prev_quality
    
    return text_added, rewritten_words, citations_added, quality_change

def _format_sources_for_writer(
    sources: List[SourceDoc],
    max_summary_length: int = 3000,
    enhance_titles: bool = True
) -> List[str]:
    """
    Format sources for writer agent input.
    
    Args:
        sources: List of SourceDoc objects
        max_summary_length: Maximum length for summary text (default: 3000)
        enhance_titles: Whether to enhance titles with context (default: True)
    
    Returns:
        List of formatted summary strings
    """
    formatted = []
    for src in sources:
        # Use content (full detailed summary) if available, fallback to snippet
        summary_text = src.content if src.content else (src.snippet or "")
        # Truncate very long summaries
        if len(summary_text) > max_summary_length:
            if max_summary_length > 2000:
                # For longer limits, preserve structure
                summary_text = summary_text[:max_summary_length - 200] + "... [truncated] ..." + summary_text[-200:]
            else:
                # For shorter limits, simple truncation
                summary_text = summary_text[:max_summary_length - 20] + "... [truncated]"
        
        # Enhance title with context if requested
        title = src.title or "Untitled Source"
        if enhance_titles and len(title) < 40 and summary_text:
            # Extract key topic from summary for context
            summary_words = summary_text.split()[:8]
            if summary_words:
                topic_hint = " ".join(summary_words)
                title = f"{title} – {topic_hint[:50]}"
        
        formatted.append(f"Title: {title}\nURL: {src.url}\nSummary: {summary_text}")
    
    return formatted

class ResearchManager:
    """Orchestrates research pipeline: planning, search, file processing, follow-up, writing."""

    def __init__(
        self,
        client: Optional[AsyncOpenAI] = None,
        max_sources: int = 25,
        max_waves: int = 2,
        topk_per_query: int = 5,
        num_sources: int = 8,  # For backward compatibility
    ):
        self.client = client or make_async_client()
        self.max_sources = max_sources
        self.max_waves = max_waves
        self.topk = topk_per_query
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
        
        # Rate limiting semaphores to prevent hitting TPM limits
        self.search_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SEARCHES)
        self.summarize_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SUMMARIES)

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
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and not a placeholder.
        
        Returns False for:
        - Empty or None URLs
        - Placeholder patterns like "turn@searchX", "sourceX"
        - Invalid URL markers like "#"
        """
        if not url or url.strip() == "":
            return False
        
        url = url.strip()
        
        # Check for placeholder patterns
        if re.match(r'^turn@search\d+$', url, re.IGNORECASE):
            return False
        if re.match(r'^source\d+$', url, re.IGNORECASE):
            return False
        if url == "#" or url.startswith("#ref-"):
            return False
        if url.startswith("(Invalid URL:") or url.startswith("(No URL provided)"):
            return False
        
        # Must be a valid HTTP/HTTPS URL
        if url.startswith(('http://', 'https://')):
            return True
        
        return False
    
    def _normalize_title_for_dedup(self, title: str) -> str:
        """Normalize title for deduplication comparison.
        
        Removes extra whitespace, converts to lowercase, removes common suffixes.
        """
        if not title:
            return ""
        
        # Normalize whitespace and convert to lowercase
        normalized = re.sub(r'\s+', ' ', title.strip().lower())
        
        # Remove common trailing patterns that don't affect uniqueness
        normalized = re.sub(r'\s*[-–—]\s*(google|deepmind|developers?|blog|article|news)$', '', normalized)
        normalized = re.sub(r'\s*\|.*$', '', normalized)  # Remove everything after |
        normalized = re.sub(r'\s*\(.*\)$', '', normalized)  # Remove trailing parentheses
        
        return normalized.strip()
    
    def _titles_are_similar(self, title1: str, title2: str, threshold: float = 0.85) -> bool:
        """Check if two titles are similar enough to be considered duplicates.
        
        Uses normalized title comparison and simple similarity heuristics.
        """
        norm1 = self._normalize_title_for_dedup(title1)
        norm2 = self._normalize_title_for_dedup(title2)
        
        if not norm1 or not norm2:
            return False
        
        # Exact match after normalization
        if norm1 == norm2:
            return True
        
        # Check if one is a substring of the other (for truncated titles)
        if len(norm1) > 20 and len(norm2) > 20:
            if norm1 in norm2 or norm2 in norm1:
                return True
        
        # Simple word overlap check (if >85% of words match)
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if not words1 or not words2:
            return False
        
        # Remove very common words for comparison
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words1 = words1 - common_words
        words2 = words2 - common_words
        
        if not words1 or not words2:
            # Fall back to original word sets if all were common words
            words1 = set(norm1.split())
            words2 = set(norm2.split())
        
        intersection = words1 & words2
        union = words1 | words2
        
        if not union:
            return False
        
        similarity = len(intersection) / len(union)
        return similarity >= threshold
    
    def _prepare_sources_for_ui(self, sources: List[SourceDoc]) -> List[List[str]]:
        """Prepare sources for UI display with deduplication and URL validation.
        
        Args:
            sources: List of SourceDoc objects
            
        Returns:
            List of [title, url, type, published] lists, with:
            - Invalid URLs shown as empty string (not displayed)
            - Duplicate titles removed (keeps first occurrence with valid URL if available)
            - Sources with empty/invalid titles filtered out
        """
        if not sources:
            return []
        
        seen_titles = {}  # normalized_title -> (index, has_valid_url)
        sources_data = []
        
        for src in sources:
            title = (src.title or "").strip()
            
            # Skip sources with empty or very short titles (less than 3 characters)
            # Also skip if title is just whitespace or common placeholders
            if not title or len(title) < 3:
                continue
            
            # Skip common placeholder titles
            placeholder_patterns = [
                r'^untitled\s*source$',
                r'^source\s*\d+$',
                r'^no\s*title$',
                r'^n/a$',
                r'^$',
            ]
            if any(re.match(pattern, title, re.IGNORECASE) for pattern in placeholder_patterns):
                continue
            
            # Truncate long titles
            if len(title) > 80:
                title = title[:80] + "..."
            
            url = src.url or ""
            source_type = src.source_type or "web"
            published = src.published or "N/A"
            
            # Check if URL is valid
            is_valid_url = self._is_valid_url(url)
            
            # Normalize title for deduplication
            normalized_title = self._normalize_title_for_dedup(title)
            
            # Skip if normalized title is still empty (after removing suffixes)
            if not normalized_title:
                continue
            
            # Check for duplicates
            is_duplicate = False
            for seen_norm, (seen_idx, seen_has_url) in seen_titles.items():
                if self._titles_are_similar(normalized_title, seen_norm):
                    # If current has valid URL and seen doesn't, replace it
                    if is_valid_url and not seen_has_url:
                        # Replace the previous entry
                        sources_data[seen_idx][1] = url  # Update URL
                        seen_titles[seen_norm] = (seen_idx, True)
                    # Otherwise, skip this duplicate
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue
            
            # Add to seen titles
            seen_titles[normalized_title] = (len(sources_data), is_valid_url)
            
            # Only include URL if it's valid, otherwise use empty string
            display_url = url if is_valid_url else ""
            
            sources_data.append([title, display_url, source_type, published])
        
        return sources_data

    def _merge_sources(self, new_sources: List[SourceDoc], max_total: Optional[int] = None):
        """Merge sources into global index.
        
        Args:
            new_sources: List of new sources to merge
            max_total: Optional maximum total sources to maintain. If provided, stops merging once limit is reached.
        
        Returns:
            Number of sources actually merged
        """
        merged_count = 0
        for src in new_sources:
            if max_total is not None and len(self.source_index) >= max_total:
                break
            if src.url not in self.source_index:
                self.source_index[src.url] = src
                merged_count += 1
        return merged_count
    
    def _deduplicate_sources(self, sources: List[SourceDoc]) -> List[SourceDoc]:
        """Remove duplicate sources based on title similarity, URL, and content similarity.
        
        This ensures that the same source doesn't appear multiple times in the sources list
        presented to the writer agent, preventing duplicate references in the report.
        """
        seen_sources = {}  # (normalized_title, normalized_url) -> SourceDoc
        filtered = []
        
        for src in sources:
            title = (src.title or "").strip()
            url = (src.url or "").strip()
            content = (src.content or src.snippet or "").strip()
            
            # Skip sources with empty or very short titles
            if not title or len(title) < 3:
                continue
            
            # Skip placeholder titles
            placeholder_patterns = [
                r'^untitled\s*source$',
                r'^source\s*\d+$',
                r'^no\s*title$',
                r'^n/a$',
            ]
            if any(re.match(pattern, title, re.IGNORECASE) for pattern in placeholder_patterns):
                continue
            
            # Normalize title and URL for comparison
            normalized_title = self._normalize_title_for_dedup(title)
            if not normalized_title:
                continue
            
            # Normalize URL (use empty string if invalid)
            normalized_url = url if self._is_valid_url(url) else ""
            
            # Check for duplicates by title similarity and URL
            is_duplicate = False
            for (seen_title, seen_url), seen_src in seen_sources.items():
                # Check title similarity
                if self._titles_are_similar(normalized_title, seen_title):
                    # If URLs match (both valid and same, or both invalid), it's a duplicate
                    if (normalized_url and seen_url and normalized_url == seen_url) or \
                       (not normalized_url and not seen_url):
                        is_duplicate = True
                        break
                    # If current has valid URL and seen doesn't, prefer current
                    if normalized_url and not seen_url:
                        # Replace the seen one
                        seen_sources[(normalized_title, normalized_url)] = src
                        # Remove old entry from filtered list and add new one
                        filtered = [s for s in filtered if s != seen_src]
                        break
                    # If seen has valid URL and current doesn't, skip current
                    if seen_url and not normalized_url:
                        is_duplicate = True
                        break
            
            if is_duplicate:
                continue
            
            # Add to seen sources and filtered list
            seen_sources[(normalized_title, normalized_url)] = src
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
        """Helper: Summarize a list of source items in parallel and return SourceDoc objects.
        
        Uses semaphore to limit concurrent summarization calls to avoid rate limits.
        """
        if not source_items:
            return []
        
        async def summarize_with_semaphore(item: Tuple[SourceItem, Dict]) -> Optional[str]:
            """Summarize a single source item with semaphore protection."""
            async with self.summarize_semaphore:
                try:
                    return await self.search_agent.summarize_result_async(item[0])
                except Exception as e:
                    print(f"Warning: Failed to summarize result {item[0].title}: {e}")
                    return None
        
        tasks = [summarize_with_semaphore(item) for item in source_items]
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
        self, queries: List[str], status_messages: List[str], max_results_per_query: Optional[int] = None
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
            max_results_per_query: Optional limit on results per query. If None, uses self.topk
        
        Returns:
            Tuple of (sources, query_summaries):
            - sources: List of SourceDoc objects (deduplicated by URL)
            - query_summaries: List of query-level summary strings for report context
        
        All queries are processed concurrently, and result summarization within each query
        is also parallelized for optimal performance.
        """
        # Use provided limit or default to self.topk
        effective_topk = max_results_per_query if max_results_per_query is not None else self.topk
        unique_sources = []
        query_summaries = []

        async def process_single_query(q: str) -> Tuple[List[SourceDoc], Optional[str]]:
            """Process a single query and return (sources, query_summary)."""
            # Use semaphore to limit concurrent searches
            async with self.search_semaphore:
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
                    results_to_process = cached_results[:effective_topk]
                    
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
                        
                        # Limit to effective_topk
                        web_results = web_results[:effective_topk]
                        
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

        # Process queries with controlled concurrency (semaphore handles batching)
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
    ) -> AsyncGenerator[Tuple[str, str, Optional[object]], None]:
        """Execute multi-wave research pipeline. Yields (report_md, status_text, analytics)."""
        if approved_queries:
            queries = approved_queries

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
        
        # Track previous report for cross-wave comparison
        previous_report: Optional[ResearchReport] = None

        # Initial status message
        status_messages.append(f"🚀 Starting research on: {topic}")
        status_messages.append("=" * 60)
        
        # Generate queries if not provided
        recommended_source_count = None
        if not queries:
            status_messages.append("🔍 Generating search queries...")
            yield ("", "\n\n".join(status_messages), None)
            query_response = await self.planner.generate_async(topic)
            queries = query_response.queries
            status_messages.append(f"✅ Generated {len(queries)} search queries")
            
            # Get recommended source count from planner if available
            if hasattr(query_response, 'recommended_source_count') and query_response.recommended_source_count:
                recommended_source_count = query_response.recommended_source_count
                # Use recommended count if max_sources wasn't explicitly set (default is 25)
                if self.max_sources == 25:  # Default value, likely not user-specified
                    self.max_sources = recommended_source_count
                    status_messages.append(f"💡 Recommended source count: {recommended_source_count} (based on query complexity)")
        else:
            # Use all provided queries - don't limit them
            status_messages.append(f"📋 Using {len(queries)} provided queries")
        
        status_messages.append(f"⚙️ Configuration: {waves_total} wave(s), targeting up to {self.max_sources} sources")
        status_messages.append("")

        # Generate trace ID
        trace_id = gen_trace_id()
        trace_url = f"{TRACE_DASHBOARD}{trace_id}"
        status_messages.append(f"🔗 Trace: {trace_url}")

        yield ("", "\n\n".join(status_messages), None)

        with trace("Research trace", trace_id=trace_id):
            # ----------- FILE SUMMARIES (WAVE 0) ----------
            if uploaded_files:
                status_messages.append(f"📂 Found {len(uploaded_files)} user-uploaded file(s).")
                yield ("", "\n\n".join(status_messages), None)

                files_summaries = await self.process_uploaded_files(
                    uploaded_files, status_messages
                )
                merged_files = self._merge_sources(files_summaries, max_total=self.max_sources)
                status_messages.append(f"📁 File processing completed. Merged {merged_files} file source(s).\n")
                yield ("", "\n\n".join(status_messages), None)

            # ----------- MULTI-WAVE SEARCH ----------
            while wave <= waves_total:
                wave_start_time = time.monotonic()
                status_messages.append(f"🌊 Starting Wave {wave}/{waves_total}")
                yield ("", "\n\n".join(status_messages), None)

                # Track queries for this wave
                wave_queries_count = len(queries)
                all_queries_used.extend(queries)
                
                # Calculate dynamic topk_per_query based on max_sources and remaining capacity
                # Ensure we don't exceed max_sources across all queries
                sources_already_discovered = len(self.source_index)
                remaining_capacity = max(0, self.max_sources - sources_already_discovered)
                
                # Calculate topk per query: distribute remaining capacity across queries
                # Use floor division to be conservative and ensure we don't exceed max_sources
                max_results_per_query = None
                if wave_queries_count > 0 and remaining_capacity > 0:
                    # Calculate conservatively: floor division ensures we don't exceed
                    calculated_topk = max(1, remaining_capacity // wave_queries_count)
                    # Don't exceed the configured topk
                    calculated_topk = min(calculated_topk, self.topk)
                    if calculated_topk < self.topk:
                        max_results_per_query = calculated_topk
                        status_messages.append(f"ℹ️ Limiting to {calculated_topk} results per query to stay within {self.max_sources} total sources")
                
                # Show queries being executed for this wave
                if wave == 1:
                    status_messages.append(f"📝 Executing {wave_queries_count} search queries for this wave...")
                else:
                    status_messages.append(f"📝 Executing {wave_queries_count} follow-up queries for this wave...")
                yield ("", "\n\n".join(status_messages), None)
                
                # Step 1 — Web search (pass max_results_per_query as parameter)
                wave_sources, wave_query_summaries = await self.run_web_search(
                    queries, status_messages, max_results_per_query=max_results_per_query
                )
                
                # Collect query-level summaries
                all_query_summaries.extend(wave_query_summaries)
                
                # Track sources discovered in this wave
                wave_sources_count = len(wave_sources)

                # Merge sources with max_sources limit (stops merging once limit is reached)
                merged_count = self._merge_sources(wave_sources, max_total=self.max_sources)
                
                # Calculate wave duration
                wave_duration = time.monotonic() - wave_start_time
                
                # Check if we've reached max_sources limit
                current_total = len(self.source_index)
                if current_total >= self.max_sources:
                    status_messages.append(f"✅ Wave {wave} complete: Merged {merged_count} new sources in {wave_duration:.1f}s")
                    status_messages.append(f"🧮 Total unique sources: {current_total} (reached limit of {self.max_sources})")
                    yield ("", "\n\n".join(status_messages), None)
                    # Stop searching if we've reached the limit
                    status_messages.append(f"✔ Source limit reached. Ending search waves.\n")
                    yield ("", "\n\n".join(status_messages), None)
                    break
                else:
                    status_messages.append(f"✅ Wave {wave} complete: Merged {merged_count} new sources in {wave_duration:.1f}s")
                    status_messages.append(f"🧮 Total unique sources so far: {current_total} (limit: {self.max_sources})")
                    yield ("", "\n\n".join(status_messages), None)
                
                # Generate intermediate report for cross-wave comparison
                # Only if we have enough sources (at least 3) to make it meaningful
                current_report = None
                text_added = None
                text_rewritten = None
                citations_added = None
                quality_change = None
                
                if len(self.source_index) >= 3:
                    try:
                        # Prepare sources for intermediate report
                        intermediate_sources = list(self.source_index.values())[:min(15, len(self.source_index))]
                        filtered_intermediate = self._filter_top_sources(intermediate_sources, top_k=min(10, len(intermediate_sources)))
                        
                        # Format summaries for writer (simplified for intermediate reports)
                        intermediate_summaries = _format_sources_for_writer(
                            filtered_intermediate,
                            max_summary_length=2000,
                            enhance_titles=False
                        )
                        
                        # Generate intermediate report
                        intermediate_subtopics = self._extract_subtopic_themes(all_queries_used, topic=topic)
                        if not intermediate_subtopics:
                            intermediate_subtopics = [topic[:60]]
                        
                        query_summaries_text = "\n\n".join(all_query_summaries[:5]) if all_query_summaries else ""
                        
                        current_report = await self.writer.draft_async(
                            topic=topic,
                            subtopics=intermediate_subtopics[:5],
                            summaries=intermediate_summaries[:10],
                            sources=filtered_intermediate[:10],
                            query_level_summaries=query_summaries_text[:1000] if query_summaries_text else "",
                        )
                        
                        # Calculate deltas
                        text_added, text_rewritten, citations_added, quality_change = _calculate_report_deltas(
                            previous_report, current_report
                        )
                        
                        # Update previous report for next wave
                        previous_report = current_report
                        
                    except Exception as e:
                        # If intermediate report generation fails, continue without it
                        status_messages.append(f"⚠️ Could not generate intermediate report for wave {wave}: {e}")
                
                # Record wave statistics with cross-wave improvement metrics
                wave_stats_list.append(
                    WaveStat(
                        wave_index=wave,
                        num_queries=wave_queries_count,
                        num_sources_discovered=wave_sources_count,
                        duration_seconds=wave_duration,
                        wave_text_added=text_added,
                        wave_text_rewritten=text_rewritten,
                        wave_citations_added=citations_added,
                        wave_quality_change_score=quality_change,
                    )
                )

                # Step 2 — Follow-Up Decision
                status_messages.append(
                    "🤔 Evaluating whether another research wave is needed based on current coverage and gaps..."
                )
                yield ("", "\n\n".join(status_messages), None)

                # Build findings text for follow-up decision
                findings_sections: List[str] = []
                findings_sections.append(f"Topic: {topic}")
                findings_sections.append(f"Sources found: {len(self.source_index)}")

                # Summaries of top sources discovered so far
                source_lines = []
                for i, src in enumerate(list(self.source_index.values())[:10], 1):
                    source_lines.append(f"{i}. {src.title} - {src.snippet[:160]}...")
                if source_lines:
                    findings_sections.append("Recent sources (top 10):\n" + "\n".join(source_lines))

                # Include prior queries so follow-up agent avoids duplicates
                if all_queries_used:
                    prior_query_lines = []
                    for i, q in enumerate(all_queries_used[-20:], 1):
                        prior_query_lines.append(f"{i}. {q}")
                    findings_sections.append(
                        "Previous queries already executed (avoid repeating unless narrowing a specific angle):\n"
                        + "\n".join(prior_query_lines)
                    )

                findings_text = "\n\n".join(findings_sections) + "\n"

                followup = await self.followup_agent.decide_async(
                    original_query=topic,
                    findings_text=findings_text,
                )

                # Dedupe follow-up queries against all prior queries
                prev_queries_norm = {q.lower().strip() for q in all_queries_used if q}
                new_followup_queries: List[str] = []
                seen_followups: Set[str] = set()
                dropped_prev = 0
                dropped_internal = 0
                for q in followup.queries or []:
                    if not q:
                        continue
                    q_stripped = q.strip()
                    if not q_stripped:
                        continue
                    q_norm = q_stripped.lower()
                    if q_norm in prev_queries_norm:
                        dropped_prev += 1
                        continue
                    if q_norm in seen_followups:
                        dropped_internal += 1
                        continue
                    seen_followups.add(q_norm)
                    new_followup_queries.append(q_stripped)

                total_dropped = dropped_prev + dropped_internal
                if total_dropped:
                    details = []
                    if dropped_prev:
                        details.append(f"{dropped_prev} matched previous queries")
                    if dropped_internal:
                        details.append(f"{dropped_internal} were duplicates within follow-ups")
                    status_messages.append(
                        "ℹ️ Dropped "
                        + " and ".join(details)
                        + " from follow-up suggestions to avoid re-searching the same angle."
                    )

                if not new_followup_queries:
                    status_messages.append(
                        "✔ No genuinely new follow-up queries remained after deduplication. Ending search waves.\n"
                    )
                    yield ("", "\n\n".join(status_messages), None)
                    break

                if not followup.should_follow_up or wave == waves_total:
                    status_messages.append(f"✔ No more follow-ups required. Ending search waves.\n")
                    yield ("", "\n\n".join(status_messages), None)
                    break

                queries = new_followup_queries
                wave += 1
                status_messages.append(
                    f"🔄 Follow-up queries generated: using {len(queries)} new query(ies) (after dropping duplicates)."
                )
                yield ("", "\n\n".join(status_messages), None)

            # ----------- FINAL WRITING ----------
            status_messages.append("✍️ Writing final long-form report...")
            yield ("", "\n\n".join(status_messages), None)

            all_sources_list = list(self.source_index.values())[:self.max_sources]
            
            # Filter and deduplicate sources before writing
            # Use max_sources for filtering, but ensure we don't exceed it
            filter_top_k = min(self.max_sources, len(all_sources_list))
            filtered_sources = self._filter_top_sources(all_sources_list, top_k=filter_top_k)
            status_messages.append(f"📝 Filtered to {len(filtered_sources)} unique sources (from {len(all_sources_list)})")

            # Format sources for writer - truncate long summaries and enhance titles
            summaries = _format_sources_for_writer(
                filtered_sources,
                max_summary_length=5000,
                enhance_titles=True
            )

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
                if len(query_level_summaries_text) > 5000:
                    query_level_summaries_text = query_level_summaries_text[:4500] + "... [truncated]"

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
            
            # Calculate deltas for final report only if we haven't already calculated them
            # (i.e., if the final report is different from the last intermediate report)
            # The final report uses more sources, so it may have improvements
            if previous_report is not None and len(wave_stats_list) > 0:
                last_wave_stat = wave_stats_list[-1]
                # Only recalculate if we haven't already calculated deltas for this wave
                # or if the final report might be significantly different (uses more sources)
                if last_wave_stat.wave_text_added is None:
                    final_text_added, final_text_rewritten, final_citations_added, final_quality_change = _calculate_report_deltas(
                        previous_report, final_report
                    )
                    # Update the last wave stat with final deltas
                    wave_stats_list[-1] = WaveStat(
                        wave_index=last_wave_stat.wave_index,
                        num_queries=last_wave_stat.num_queries,
                        num_sources_discovered=last_wave_stat.num_sources_discovered,
                        duration_seconds=last_wave_stat.duration_seconds,
                        wave_text_added=final_text_added,
                        wave_text_rewritten=final_text_rewritten,
                        wave_citations_added=final_citations_added,
                        wave_quality_change_score=final_quality_change,
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

            # Calculate total duration
            total_duration = time.monotonic() - start_time
            
            status_messages.append("📄 Report complete.\n")
            status_messages.append("=" * 60)
            status_messages.append(f"✅ Research Summary:")
            status_messages.append(f"   • Total duration: {total_duration:.1f}s")
            status_messages.append(f"   • Waves completed: {wave}")
            status_messages.append(f"   • Queries executed: {self.metrics_queries_executed}")
            status_messages.append(f"   • Sources discovered: {len(self.source_index)}")
            status_messages.append(f"   • Sources used in report: {len(filtered_sources)}")
            status_messages.append(f"   • Report sections: {len(final_report.sections)}")
            if self.metrics_cache_hits + self.metrics_cache_misses > 0:
                cache_rate = (self.metrics_cache_hits / (self.metrics_cache_hits + self.metrics_cache_misses)) * 100
                status_messages.append(f"   • Cache hit rate: {cache_rate:.1f}%")
            status_messages.append("=" * 60)

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

            # Yield final report without sources_data (references are in the report markdown)
            yield (md, "\n\n".join(status_messages), analytics)

    # -----------------------------------------------------------
    # PLANNING WRAPPER
    # -----------------------------------------------------------

    async def generate_plan(self, topic: str) -> QueryResponse:
        """Generate initial search plan with queries and thoughts.
           Planner decides query count based on topic complexity,"""
        return await self.planner.generate_async(topic)
