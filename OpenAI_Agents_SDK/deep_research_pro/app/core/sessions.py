from __future__ import annotations
from pathlib import Path

# Placeholder for a future SQLite-backed session.
# Keep a no-op function so iteration 0 runs without the SDK.
def get_session(db_path: Path) -> dict:
    """
    Return a simple dict acting as a placeholder 'session'.
    We will replace this with an actual Agents SDK SQLiteSession in Iteration 1+.
    """
    return {"db_path": str(db_path)}