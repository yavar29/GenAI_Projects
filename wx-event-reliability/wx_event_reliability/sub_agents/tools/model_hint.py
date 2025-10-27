from __future__ import annotations
from typing import Dict, Any
import re
from google.adk.tools import FunctionTool

@FunctionTool
def detect_model_hint(user_query: str) -> Dict[str, Any]:
    """
    Parse model preferences (metadata only). Supports: gfs, ecmwf, era5, icon, best, auto.
    """
    q = user_query.lower()
    hint = None
    if "gfs" in q: hint = "gfs"
    elif "ecmwf" in q: hint = "ecmwf"
    elif "era5" in q: hint = "era5"
    elif "icon" in q: hint = "icon"
    elif "best" in q: hint = "best"
    elif "auto" in q: hint = "auto"
    return {"model_hint": hint}


