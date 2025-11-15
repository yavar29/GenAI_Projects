"""
Unit tests for CacheManager.

Tests cache operations, TTL, LRU, and time-sensitive query detection.
"""

import pytest
import tempfile
import os
import time
from pathlib import Path
from app.core.cache_manager import CacheManager, TIME_SENSITIVE_KEYWORDS


@pytest.fixture
def temp_cache_db():
    """Create a temporary cache database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "test_cache.sqlite"
        manager = CacheManager(
            ttl_seconds=3600,  # 1 hour for testing
            max_rows=10,  # Small limit for testing
            version_salt="test_v1",
        )
        manager.db_path = cache_path
        manager._init_db()
        yield manager
        # Cleanup
        if cache_path.exists():
            cache_path.unlink()


def test_cache_set_and_get(temp_cache_db):
    """Test basic cache set and get operations."""
    query = "test query"
    results = [{"title": "Test", "url": "https://example.com", "snippet": "Test snippet"}]
    summary = "Test summary"
    
    # Set cache
    temp_cache_db.set(query, results, summary)
    
    # Get from cache
    cached = temp_cache_db.get(query)
    
    assert cached is not None
    cached_results, cached_summary = cached
    assert cached_results == results
    assert cached_summary == summary


def test_cache_ttl_expiration(temp_cache_db):
    """Test that cache entries expire after TTL."""
    query = "test query"
    results = [{"title": "Test", "url": "https://example.com"}]
    
    # Set with short TTL
    temp_cache_db.ttl_seconds = 1  # 1 second TTL
    temp_cache_db.set(query, results, None)
    
    # Should be available immediately
    assert temp_cache_db.get(query) is not None
    
    # Wait for expiration
    time.sleep(1.1)
    
    # Should be expired
    assert temp_cache_db.get(query) is None


def test_cache_time_sensitive_bypass(temp_cache_db):
    """Test that time-sensitive queries bypass cache."""
    for keyword in TIME_SENSITIVE_KEYWORDS[:5]:  # Test first 5 keywords
        query = f"latest news about {keyword}"
        
        # Should not cache time-sensitive queries
        temp_cache_db.set(query, [{"title": "Test"}], None)
        
        # Should return None (bypassed)
        assert temp_cache_db.get(query) is None


def test_cache_lru_pruning(temp_cache_db):
    """Test that cache prunes old entries when max_rows exceeded."""
    # Fill cache beyond max_rows
    for i in range(15):  # max_rows is 10
        temp_cache_db.set(f"query {i}", [{"title": f"Result {i}"}], None)
    
    # Should have pruned to max_rows
    stats = temp_cache_db.get_stats()
    assert stats["total_entries"] <= temp_cache_db.max_rows


def test_cache_cleanup(temp_cache_db):
    """Test cache cleanup removes expired entries."""
    # Add some entries
    for i in range(5):
        temp_cache_db.set(f"query {i}", [{"title": f"Result {i}"}], None)
    
    # Manually expire them by setting old timestamp
    import sqlite3
    conn = sqlite3.connect(str(temp_cache_db.db_path))
    cursor = conn.cursor()
    old_timestamp = int(time.time()) - 7200  # 2 hours ago
    cursor.execute("UPDATE qcache SET ts = ?", (old_timestamp,))
    conn.commit()
    conn.close()
    
    # Cleanup
    expired_count, old_count = temp_cache_db.cleanup(aggressive=False)
    
    # Should have removed expired entries
    assert expired_count >= 0
    stats = temp_cache_db.get_stats()
    assert stats["expired_entries"] == 0  # Should be cleaned


def test_cache_get_stats(temp_cache_db):
    """Test cache statistics reporting."""
    # Add some entries
    temp_cache_db.set("query 1", [{"title": "Result 1"}], "Summary 1")
    temp_cache_db.set("query 2", [{"title": "Result 2"}], "Summary 2")
    
    stats = temp_cache_db.get_stats()
    
    assert "total_entries" in stats
    assert "valid_entries" in stats
    assert "expired_entries" in stats
    assert "l1_entries" in stats
    assert "size_mb" in stats
    assert stats["total_entries"] >= 2


def test_cache_clear(temp_cache_db):
    """Test that cache clear removes all entries."""
    # Add entries
    for i in range(5):
        temp_cache_db.set(f"query {i}", [{"title": f"Result {i}"}], None)
    
    # Clear
    temp_cache_db.clear()
    
    # Should be empty
    stats = temp_cache_db.get_stats()
    assert stats["total_entries"] == 0
    assert len(temp_cache_db.l1_cache) == 0

