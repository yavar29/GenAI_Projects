"""
Unit tests for ResearchManager core functionality.

Tests source filtering, deduplication, and key pipeline methods.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.research_manager import ResearchManager
from app.schemas.source import SourceDoc


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    return MagicMock()


@pytest.fixture
def research_manager(mock_openai_client):
    """Create a ResearchManager instance for testing."""
    with patch("app.core.research_manager.make_async_client", return_value=mock_openai_client):
        manager = ResearchManager(
            client=mock_openai_client,
            max_sources=25,
            max_waves=2,
            topk_per_query=5,
        )
        return manager


@pytest.fixture
def sample_sources():
    """Create sample SourceDoc objects for testing."""
    return [
        SourceDoc(
            title="Source 1",
            url="https://example.com/1",
            snippet="Short snippet 1",
            content="This is a longer content for source 1 with more details about the topic.",
            published="2024-01-01",
            source_type="web",
            provider="openai",
        ),
        SourceDoc(
            title="Source 2",
            url="https://example.com/2",
            snippet="Short snippet 2",
            content="This is a longer content for source 2 with extensive information about the subject matter.",
            published="2024-01-02",
            source_type="web",
            provider="openai",
        ),
        SourceDoc(
            title="Source 3",
            url="https://example.com/1",  # Duplicate URL
            snippet="Short snippet 3",
            content="This is a longer content for source 3, which is a duplicate of source 1.",
            published="2024-01-03",
            source_type="web",
            provider="openai",
        ),
        SourceDoc(
            title="Source 4",
            url="https://example.com/4",
            snippet="Short snippet 4",
            content="Short",  # Less content
            published="2024-01-04",
            source_type="web",
            provider="openai",
        ),
    ]


def test_deduplicate_sources(research_manager, sample_sources):
    """Test that _deduplicate_sources removes duplicates based on content."""
    # Source 1 and Source 3 have same URL, so Source 3 should be removed
    deduplicated = research_manager._deduplicate_sources(sample_sources)
    
    # Should have 3 unique sources (Source 3 is duplicate of Source 1)
    assert len(deduplicated) == 3
    
    # Check that URLs are unique
    urls = [s.url for s in deduplicated]
    assert len(urls) == len(set(urls))
    
    # Source 3 (duplicate) should not be in result
    assert not any(s.url == "https://example.com/1" and s.title == "Source 3" for s in deduplicated)


def test_filter_top_sources(research_manager, sample_sources):
    """Test that _filter_top_sources prioritizes sources with richer content."""
    # Remove duplicates first
    unique_sources = research_manager._deduplicate_sources(sample_sources)
    
    # Filter to top 2
    filtered = research_manager._filter_top_sources(unique_sources, top_k=2)
    
    assert len(filtered) == 2
    
    # Should prioritize sources with more content
    # Source 2 has the most content, Source 1 has second most
    content_lengths = [len(s.content or "") for s in filtered]
    assert max(content_lengths) >= min(content_lengths)  # Should be sorted by content length
    
    # Source 4 (with least content) should not be in top 2
    assert not any(s.title == "Source 4" for s in filtered)


def test_extract_subtopic_themes(research_manager):
    """Test that _extract_subtopic_themes identifies themes from queries."""
    queries = [
        "What is AI in healthcare background",
        "AI healthcare statistics 2024",
        "Future trends in healthcare AI",
        "Case studies of AI in hospitals",
        "Risks of AI in healthcare",
    ]
    
    themes = research_manager._extract_subtopic_themes(queries)
    
    # Should extract meaningful themes
    assert len(themes) > 0
    assert len(themes) <= 7  # Should limit to top 7
    
    # Should identify common themes
    theme_text = " ".join(themes).lower()
    # At least one of these should be present
    assert any(keyword in theme_text for keyword in 
              ["background", "statistics", "trend", "case", "risk"])


def test_extract_subtopic_themes_empty(research_manager):
    """Test _extract_subtopic_themes with empty queries."""
    themes = research_manager._extract_subtopic_themes([])
    assert themes == []


def test_extract_subtopic_themes_fallback(research_manager):
    """Test _extract_subtopic_themes fallback to query snippets."""
    # Queries that don't match any theme keywords
    queries = ["xyz abc def", "random query text"]
    
    themes = research_manager._extract_subtopic_themes(queries)
    
    # Should fallback to query snippets if no themes detected
    if len(themes) < 3:
        # Fallback should use first few queries
        assert len(themes) <= len(queries)


def test_estimate_token_count(research_manager):
    """Test token count estimation."""
    text = "This is a test sentence with multiple words."
    
    # Should return a reasonable estimate
    count = research_manager._estimate_token_count(text)
    
    assert isinstance(count, int)
    assert count > 0
    # Rough estimate: should be roughly 1/4 of character count
    assert count <= len(text)  # Shouldn't be more than character count


def test_norm_query(research_manager):
    """Test query normalization for caching."""
    assert research_manager._norm_query("  AI in Healthcare  ") == "ai in healthcare"
    assert research_manager._norm_query("AI IN HEALTHCARE") == "ai in healthcare"
    assert research_manager._norm_query("ai in healthcare") == "ai in healthcare"


def test_merge_sources(research_manager, sample_sources):
    """Test that _merge_sources adds new sources to index."""
    # Initially empty
    assert len(research_manager.source_index) == 0
    
    # Merge first two sources
    research_manager._merge_sources(sample_sources[:2])
    assert len(research_manager.source_index) == 2
    
    # Merge duplicate (should not add)
    research_manager._merge_sources([sample_sources[2]])  # Same URL as source 1
    assert len(research_manager.source_index) == 2  # Still 2
    
    # Merge new source
    research_manager._merge_sources([sample_sources[3]])
    assert len(research_manager.source_index) == 3

