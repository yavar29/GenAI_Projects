"""
Advanced caching system with SQLite persistence, TTL management, and intelligent invalidation.
"""

from __future__ import annotations

import sqlite3
import json
import time
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

from app.core.settings import DATA_DIR

# Cache configuration
CACHE_DB_PATH = DATA_DIR / "search_cache_v1.sqlite"
CACHE_TTL_SECONDS = 24 * 3600  # 24 hours default
CACHE_MAX_ROWS = 1000
CACHE_VERSION_SALT = "v1.0"  # Increment to invalidate all cache
CACHE_CLEANUP_INTERVAL = 3600  # Cleanup every hour (if called)
CACHE_LAST_ACCESS_THRESHOLD = 7 * 24 * 3600  # Prune entries not accessed in 7 days

# Time-sensitive keywords that should bypass cache
TIME_SENSITIVE_KEYWORDS = [
    "today", "yesterday", "this week", "this month", "recent", "latest", "new",
    "breaking", "current", "now", "2024", "2025", "just", "announced", "happening"
]


class CacheManager:
    """
    Two-level cache system:
    - L1: In-memory dict for fast access during session
    - L2: SQLite disk cache for persistence across restarts
    """
    
    def __init__(
        self,
        ttl_seconds: int = CACHE_TTL_SECONDS,
        max_rows: int = CACHE_MAX_ROWS,
        version_salt: str = CACHE_VERSION_SALT,
    ):
        self.ttl_seconds = ttl_seconds
        self.max_rows = max_rows
        self.version_salt = version_salt
        self.db_path = CACHE_DB_PATH
        
        # L1: In-memory cache
        self.l1_cache: Dict[str, Tuple[List[Dict], Optional[str], float]] = {}
        
        # Initialize L2: SQLite cache
        self._init_db()
        
        # Track last cleanup time
        self._last_cleanup = time.time()
    
    def _init_db(self):
        """Initialize SQLite cache database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='qcache'
        """)
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            # Create new table with all columns
            cursor.execute("""
                CREATE TABLE qcache (
                    k TEXT PRIMARY KEY,
                    v TEXT NOT NULL,
                    ts INTEGER NOT NULL,
                    last_access INTEGER NOT NULL,
                    access_count INTEGER DEFAULT 1
                )
            """)
        else:
            # Migrate existing table: add new columns if they don't exist
            cursor.execute("PRAGMA table_info(qcache)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if "last_access" not in columns:
                cursor.execute("ALTER TABLE qcache ADD COLUMN last_access INTEGER")
                # Set last_access to ts for existing entries
                cursor.execute("UPDATE qcache SET last_access = ts WHERE last_access IS NULL")
            
            if "access_count" not in columns:
                cursor.execute("ALTER TABLE qcache ADD COLUMN access_count INTEGER DEFAULT 1")
                cursor.execute("UPDATE qcache SET access_count = 1 WHERE access_count IS NULL")
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ts ON qcache(ts)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_last_access ON qcache(last_access)
        """)
        
        conn.commit()
        conn.close()
    
    def _make_key(self, query: str) -> str:
        """Create cache key with version salt."""
        normalized = query.lower().strip()
        return f"{self.version_salt}|{normalized}"
    
    def _is_time_sensitive(self, query: str) -> bool:
        """Check if query is time-sensitive and should bypass cache."""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in TIME_SENSITIVE_KEYWORDS)
    
    def get(self, query: str) -> Optional[Tuple[List[Dict], Optional[str]]]:
        """
        Get cached results for a query.
        Returns (results, summary) or None if not found/expired.
        """
        # Check if query is time-sensitive
        if self._is_time_sensitive(query):
            return None
        
        key = self._make_key(query)
        now = time.time()
        
        # Check L1 cache first
        if key in self.l1_cache:
            results, summary, cached_time = self.l1_cache[key]
            if now - cached_time < self.ttl_seconds:
                return (results, summary)
            else:
                # Expired in L1, remove it
                del self.l1_cache[key]
        
        # Check L2 cache (SQLite)
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT v, ts FROM qcache WHERE k = ?",
                (key,)
            )
            row = cursor.fetchone()
            
            if row:
                data_json, cached_ts = row
                age = now - cached_ts
                
                if age < self.ttl_seconds:
                    # Valid cache entry
                    data = json.loads(data_json)
                    results = data.get("results", [])
                    summary = data.get("summary")
                    
                    # Update last_access and access_count
                    cursor.execute(
                        "UPDATE qcache SET last_access = ?, access_count = access_count + 1 WHERE k = ?",
                        (int(now), key)
                    )
                    conn.commit()
                    
                    # Populate L1 cache
                    self.l1_cache[key] = (results, summary, now)
                    
                    return (results, summary)
                else:
                    # Expired, remove it
                    cursor.execute("DELETE FROM qcache WHERE k = ?", (key,))
                    conn.commit()
        finally:
            conn.close()
        
        return None
    
    def set(self, query: str, results: List[Dict], summary: Optional[str] = None):
        """Store results in both L1 and L2 cache."""
        # Don't cache time-sensitive queries
        if self._is_time_sensitive(query):
            return
        
        key = self._make_key(query)
        now = time.time()
        
        # Store in L1
        self.l1_cache[key] = (results, summary, now)
        
        # Store in L2 (SQLite)
        data = {
            "results": results,
            "summary": summary,
        }
        data_json = json.dumps(data)
        
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        cursor = conn.cursor()
        
        try:
            # Use INSERT OR REPLACE to update existing entries
            cursor.execute(
                """
                INSERT OR REPLACE INTO qcache (k, v, ts, last_access, access_count)
                VALUES (?, ?, ?, ?, 
                    COALESCE((SELECT access_count FROM qcache WHERE k = ?), 0) + 1)
                """,
                (key, data_json, int(now), int(now), key)
            )
            conn.commit()
            
            # Prune if needed (check size)
            self._prune_if_needed(cursor, conn)
        finally:
            conn.close()
        
        # Periodic cleanup (every hour)
        if now - self._last_cleanup > CACHE_CLEANUP_INTERVAL:
            self.cleanup()
            self._last_cleanup = now
    
    def _prune_if_needed(self, cursor: sqlite3.Cursor, conn: sqlite3.Connection):
        """Prune cache if it exceeds max_rows."""
        cursor.execute("SELECT COUNT(*) FROM qcache")
        count = cursor.fetchone()[0]
        
        if count > self.max_rows:
            # Remove oldest entries (by last_access) until under limit
            excess = count - self.max_rows
            cursor.execute(
                """
                DELETE FROM qcache 
                WHERE k IN (
                    SELECT k FROM qcache 
                    ORDER BY last_access ASC 
                    LIMIT ?
                )
                """,
                (excess,)
            )
            conn.commit()
    
    def cleanup(self, aggressive: bool = False):
        """
        Clean up expired and old cache entries.
        
        Args:
            aggressive: If True, also remove entries not accessed in 7 days
        """
        now = time.time()
        expired_threshold = now - self.ttl_seconds
        
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        cursor = conn.cursor()
        
        try:
            # Remove expired entries
            cursor.execute(
                "DELETE FROM qcache WHERE ts < ?",
                (int(expired_threshold),)
            )
            expired_count = cursor.rowcount
            
            # Aggressive cleanup: remove entries not accessed recently
            old_count = 0
            if aggressive:
                old_threshold = now - CACHE_LAST_ACCESS_THRESHOLD
                cursor.execute(
                    "DELETE FROM qcache WHERE last_access < ?",
                    (int(old_threshold),)
                )
                old_count = cursor.rowcount
            
            conn.commit()
            
            # Also clean L1 cache
            expired_keys = [
                k for k, (_, _, cached_time) in self.l1_cache.items()
                if now - cached_time >= self.ttl_seconds
            ]
            for k in expired_keys:
                del self.l1_cache[k]
            
            return expired_count, old_count
        finally:
            conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        cursor = conn.cursor()
        
        try:
            # Total entries
            cursor.execute("SELECT COUNT(*) FROM qcache")
            total = cursor.fetchone()[0]
            
            # Expired entries
            now = time.time()
            expired_threshold = now - self.ttl_seconds
            cursor.execute("SELECT COUNT(*) FROM qcache WHERE ts < ?", (int(expired_threshold),))
            expired = cursor.fetchone()[0]
            
            # Old entries (not accessed in 7 days)
            old_threshold = now - CACHE_LAST_ACCESS_THRESHOLD
            cursor.execute("SELECT COUNT(*) FROM qcache WHERE last_access < ?", (int(old_threshold),))
            old = cursor.fetchone()[0]
            
            # Cache size
            cursor.execute("SELECT SUM(LENGTH(v)) FROM qcache")
            size_bytes = cursor.fetchone()[0] or 0
            
            return {
                "total_entries": total,
                "valid_entries": total - expired,
                "expired_entries": expired,
                "old_entries": old,
                "l1_entries": len(self.l1_cache),
                "size_mb": round(size_bytes / (1024 * 1024), 2),
                "max_rows": self.max_rows,
                "ttl_hours": self.ttl_seconds / 3600,
            }
        finally:
            conn.close()
    
    def clear(self):
        """Clear all cache entries."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM qcache")
            conn.commit()
        finally:
            conn.close()
        
        self.l1_cache.clear()


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
        # Run cleanup on startup
        _cache_manager.cleanup(aggressive=False)
    return _cache_manager

