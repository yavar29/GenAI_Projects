#!/usr/bin/env python3
"""
Test script to verify caching mechanism is working.
Run this to check cache hits/misses and inspect the cache database.
"""

import sqlite3
import json
import time
import os
from pathlib import Path

# Cache configuration (matching research_manager.py)
CACHE_DB_PATH = os.path.join("data", "search_cache_v1.sqlite")
CACHE_TTL_SECONDS = 24 * 3600  # 24h

def inspect_cache():
    """Inspect the cache database contents."""
    if not os.path.exists(CACHE_DB_PATH):
        print(f"❌ Cache database not found at: {CACHE_DB_PATH}")
        print("   Run a research query first to create the cache.")
        return
    
    print(f"📊 Inspecting cache database: {CACHE_DB_PATH}\n")
    
    conn = sqlite3.connect(CACHE_DB_PATH)
    cursor = conn.cursor()
    
    # Get total entries
    cursor.execute("SELECT COUNT(*) FROM qcache")
    total = cursor.fetchone()[0]
    print(f"Total cache entries: {total}\n")
    
    # Get entries with age
    cursor.execute("SELECT k, ts, LENGTH(v) as size FROM qcache ORDER BY ts DESC LIMIT 10")
    rows = cursor.fetchall()
    
    if rows:
        print("Recent cache entries (last 10):")
        print("-" * 80)
        now = int(time.time())
        for key, timestamp, size in rows:
            age_seconds = now - timestamp
            age_hours = age_seconds / 3600
            age_str = f"{age_hours:.1f}h" if age_hours >= 1 else f"{age_seconds/60:.1f}m"
            
            # Extract query from key (remove version salt)
            query = key.split("|", 1)[-1] if "|" in key else key
            query_preview = query[:60] + "..." if len(query) > 60 else query
            
            expired = "⚠️ EXPIRED" if age_seconds > CACHE_TTL_SECONDS else "✅ Valid"
            print(f"{expired} | Age: {age_str:>6} | Size: {size:>6} bytes")
            print(f"  Query: {query_preview}")
            print()
    else:
        print("No cache entries found.")
    
    # Check for expired entries
    cursor.execute("SELECT COUNT(*) FROM qcache WHERE ts < ?", (int(time.time()) - CACHE_TTL_SECONDS,))
    expired_count = cursor.fetchone()[0]
    if expired_count > 0:
        print(f"⚠️  Found {expired_count} expired entries (will be cleaned up on next access)")
    
    conn.close()

def test_cache_workflow():
    """Test the cache workflow by simulating cache operations."""
    print("\n" + "=" * 80)
    print("🧪 Testing Cache Workflow")
    print("=" * 80 + "\n")
    
    print("To test caching:")
    print("1. Run a research query in the UI or CLI")
    print("2. Check the Live Log for cache statistics:")
    print("   - Look for: '📦 Cache: X hits • Y misses • Z entries'")
    print("3. Run the SAME query again")
    print("4. You should see cache hits increase on the second run")
    print("5. The second run should be faster (no API calls for cached queries)\n")
    
    print("Example workflow:")
    print("  First run:  '📦 Cache: 0 hits • 3 misses • 3 entries'")
    print("  Second run: '📦 Cache: 3 hits • 0 misses • 3 entries'  ← All cached!\n")

def check_cache_file():
    """Check if cache file exists and show its size."""
    cache_path = Path(CACHE_DB_PATH)
    if cache_path.exists():
        size = cache_path.stat().st_size
        size_kb = size / 1024
        print(f"✅ Cache file exists: {CACHE_DB_PATH}")
        print(f"   Size: {size_kb:.2f} KB ({size:,} bytes)")
    else:
        print(f"❌ Cache file not found: {CACHE_DB_PATH}")
        print("   The cache will be created automatically on first use.")

if __name__ == "__main__":
    print("=" * 80)
    print("🔍 Cache Verification Tool")
    print("=" * 80 + "\n")
    
    check_cache_file()
    print()
    inspect_cache()
    test_cache_workflow()
    
    print("\n" + "=" * 80)
    print("💡 Tips:")
    print("=" * 80)
    print("• Cache statistics appear in the Live Log after each search wave")
    print("• Cache hits = queries found in cache (fast, no API call)")
    print("• Cache misses = queries not in cache (requires API call)")
    print("• Cache persists across app restarts (SQLite disk cache)")
    print("• Expired entries (>24h) are automatically cleaned up")
    print("=" * 80)

