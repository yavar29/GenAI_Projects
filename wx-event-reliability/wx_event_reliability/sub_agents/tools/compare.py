from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import re
from datetime import date
import requests

from google.adk.tools import FunctionTool

# --- 1) Comparative query parsing -------------------------------------------

# Common comparative patterns:
#  - "Why is San Francisco colder than San Diego?"
#  - "Compare Denver vs. Boulder for wind"
#  - "SF versus SD yesterday"
#  - "Seattle and Portland last weekend"
_COMPARATIVE_TRIGGERS = [
    r"\bcolder than\b", r"\bwarmer than\b", r"\bhotter than\b", r"\bcooler than\b",
    r"\bvs\.?\b", r"\bversus\b", r"\bcompare\b", r"\bcompared to\b", r"\band\b"
]

@FunctionTool
def parse_comparative_query(user_query: str) -> Dict[str, Any]:
    """
    Heuristic extraction of up to two place strings for comparative queries.
    Returns:
      {"places": ["San Francisco", "San Diego"]} or {"places": []} if not confident.
    Notes:
      - This is a lightweight helper; the Agent should still call geocode_place on each string.
      - We bias toward picking two longest capitalized spans around 'than', 'vs', 'versus', 'and'.
    """
    q = user_query.strip()

    # Fast reject: if no trigger words, skip
    if not any(re.search(p, q, flags=re.I) for p in _COMPARATIVE_TRIGGERS):
        return {"places": []}

    # Try "X than Y"
    m = re.search(r"(?P<x>.+?)\b(?:colder|warmer|hotter|cooler)\s+than\b\s+(?P<y>.+?)($|[,\.\?!])", q, re.I)
    if m:
        x = m.group("x")
        y = m.group("y")
        # Trim common prefixes like "why is", "why's"
        x = re.sub(r"^\s*(why|'?why is|why's|why are|how is|how are)\s+", "", x, flags=re.I).strip()
        return {"places": [x.strip(", ."), y.strip(", .")]}

    # Try "X vs Y" / "X versus Y"
    m = re.search(r"(?P<x>.+?)\b(?:vs\.?|versus)\b\s+(?P<y>.+?)($|[,\.\?!])", q, re.I)
    if m:
        return {"places": [m.group("x").strip(", ."), m.group("y").strip(", .")]}

    # Try "X and Y" (fallback; riskier, but useful when question is "Seattle and Portland last weekend")
    m = re.search(r"(?P<x>[A-Z][\w\.\- ]+?)\s+(?:and|&)\s+(?P<y>[A-Z][\w\.\- ]+)", q)
    if m:
        return {"places": [m.group("x").strip(), m.group("y").strip()]}

    return {"places": []}


# --- 2) Two-location fetch & comparison --------------------------------------

_FORECAST = "https://api.open-meteo.com/v1/forecast"
_ARCHIVE  = "https://archive-api.open-meteo.com/v1/archive"

def _endpoint_for(start_iso: str, end_iso: str) -> str:
    today = date.today().isoformat()
    return _ARCHIVE if end_iso < today else _FORECAST

def _fetch(lat: float, lon: float, start_date: str, end_date: str,
           variables: List[str], granularity: str) -> Dict[str, Any]:
    endpoint = _endpoint_for(start_date, end_date)
    key = "hourly" if granularity == "hourly" else "daily"
    params = {
        "latitude": lat, "longitude": lon,
        "timezone": "UTC",
        "start_date": start_date, "end_date": end_date,
        key: ",".join(variables)
    }
    r = requests.get(endpoint, params=params, timeout=40)
    r.raise_for_status()
    data = r.json()
    units = data.get(f"{key}_units", {}) or {}
    block = data.get(key) or {}
    return {"endpoint": endpoint, "params": params, "units": units, "block": block}

def _primary_var(block: Dict[str, Any]) -> Optional[str]:
    for k in block.keys():
        if k != "time":
            return k
    return None

def _stats(vals: List[float]) -> Tuple[float, float, float]:
    from statistics import mean
    return (min(vals), max(vals), mean(vals))

def _fmt_unit(var: str, units: Dict[str, str]) -> str:
    u = units.get(var) or units.get(var.replace("_", "-")) or ""
    return f" {u}" if u else ""

@FunctionTool
def compare_weather(
    name_a: str, lat_a: float, lon_a: float,
    name_b: str, lat_b: float, lon_b: float,
    start_date: str, end_date: str,
    variables: List[str],
    granularity: str = "daily",
    tz_a: str = "",
    tz_b: str = ""
) -> Dict[str, Any]:
    """
    Fetch Open-Meteo for two locations and compare the first available variable.
    Returns: {"final_answer": "..."} — a concise, unit-aware comparison.
    """
    if not (-90 <= lat_a <= 90 and -180 <= lon_a <= 180 and -90 <= lat_b <= 90 and -180 <= lon_b <= 180):
        return {"final_answer": "Invalid coordinates for comparison."}

    res_a = _fetch(lat_a, lon_a, start_date, end_date, variables, granularity)
    res_b = _fetch(lat_b, lon_b, start_date, end_date, variables, granularity)

    block_a, block_b = res_a["block"], res_b["block"]
    if not block_a or not block_b:
        return {"final_answer": "Insufficient data to compare these locations for the requested window."}

    var = _primary_var(block_a) or _primary_var(block_b)
    if not var:
        return {"final_answer": "No variables returned for comparison."}

    try:
        vals_a = [float(x) for x in (block_a.get(var) or [])]
        vals_b = [float(x) for x in (block_b.get(var) or [])]
    except Exception:
        return {"final_answer": "Non-numeric data encountered; cannot compute comparison."}

    if not vals_a or not vals_b:
        return {"final_answer": f"No data for {var} in one or both locations."}

    amin_, amax_, amean_ = _stats(vals_a)
    bmin_, bmax_, bmean_ = _stats(vals_b)

    unit = _fmt_unit(var, res_a["units"] or res_b["units"] or {})

    tz_note_a = f" (local: {tz_a})" if tz_a else ""
    tz_note_b = f" (local: {tz_b})" if tz_b else ""
    window = f"{start_date}..{end_date} UTC"

    delta_mean = amean_ - bmean_
    sign = "higher" if delta_mean > 0 else ("lower" if delta_mean < 0 else "the same")

    # Build concise sentence(s)
    detail_a = f"{name_a}: min {amin_:.2f}{unit}, max {amax_:.2f}{unit}, mean {amean_:.2f}{unit}"
    detail_b = f"{name_b}: min {bmin_:.2f}{unit}, max {bmax_:.2f}{unit}, mean {bmean_:.2f}{unit}"
    comp = f"Mean {var} is {abs(delta_mean):.2f}{unit} {sign} in {name_a} than {name_b}."

    text = (
        f"Comparison for {var}{unit} over {window}.\n"
        f"- {detail_a}{tz_note_a}\n"
        f"- {detail_b}{tz_note_b}\n"
        f"{comp}"
    )

    return {"final_answer": text}



