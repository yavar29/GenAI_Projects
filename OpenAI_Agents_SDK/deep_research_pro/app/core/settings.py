from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from repo root or this subproject
load_dotenv(dotenv_path=Path(".env"))

PROJECT_NAME = os.getenv("PROJECT_NAME", "Deep Research Pro")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # optional check in run.py
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "sessions.sqlite3"  # reserved for later use
