"""
Unit tests for hosted web search URL resolution.

Tests that placeholder URLs are replaced by the tool's real citation URLs, or dropped.
"""

from app.tools.hosted_tools import _clean_url, _resolve_result_urls


CITATIONS = [
    ("Enterprise RAG Cost 2026: $15K to $150K Breakdown", "https://ortemtech.com/blog/rag-cost/?utm_source=openai"),
    ("RAG vs. long-context LLMs: A side-by-side comparison | Meilisearch", "https://www.meilisearch.com/blog/rag-vs-long-context-llms?utm_source=openai"),
]


def test_clean_url_strips_openai_tracking_param():
    """utm_source=openai is removed, other query params are kept."""
    assert _clean_url("https://a.com/x?utm_source=openai") == "https://a.com/x"
    assert _clean_url("https://a.com/x?id=3&utm_source=openai") == "https://a.com/x?id=3"


def test_valid_urls_are_kept():
    """Results that already have a real URL keep it (minus tracking)."""
    results = [{"title": "Anything", "url": "https://example.com/a?utm_source=openai"}]
    assert _resolve_result_urls(results, CITATIONS)[0]["url"] == "https://example.com/a"


def test_placeholder_url_is_backfilled_from_citations():
    """A placeholder URL is replaced by the citation with the closest title."""
    results = [{"title": "RAG vs. long-context LLMs: A side-by-side comparison", "url": "source"}]
    resolved = _resolve_result_urls(results, CITATIONS)
    assert resolved[0]["url"] == "https://www.meilisearch.com/blog/rag-vs-long-context-llms"


def test_unmatched_placeholder_is_dropped():
    """A result with no real URL and no matching citation is removed."""
    results = [
        {"title": "Completely unrelated title", "url": ""},
        {"title": "Kept", "url": "https://example.com/k"},
    ]
    resolved = _resolve_result_urls(results, CITATIONS)
    assert [r["title"] for r in resolved] == ["Kept"]


def test_abbreviated_url_is_treated_as_placeholder():
    """A URL the model shortened with '...' is replaced by the matching citation."""
    results = [{"title": "Enterprise RAG Cost 2026: $15K to $150K Breakdown", "url": "https://ortemtech.com/blog/..."}]
    assert _resolve_result_urls(results, CITATIONS)[0]["url"] == "https://ortemtech.com/blog/rag-cost/"


def test_abbreviated_title_is_replaced_by_citation_title():
    """A title shortened with '...' takes the real page title from the citation with the same URL."""
    results = [{"title": "Enterprise RAG Cost ... Breakdown", "url": "https://ortemtech.com/blog/rag-cost/"}]
    assert _resolve_result_urls(results, CITATIONS)[0]["title"] == "Enterprise RAG Cost 2026: $15K to $150K Breakdown"


def test_each_citation_is_used_once():
    """Two placeholder results cannot both claim the same citation."""
    results = [
        {"title": "Enterprise RAG Cost 2026", "url": ""},
        {"title": "Enterprise RAG Cost 2026", "url": "arXiv"},
    ]
    assert len(_resolve_result_urls(results, CITATIONS)) == 1
