# variables.py
from __future__ import annotations
from typing import Dict, Any, List
from google.adk.tools import FunctionTool

CANONICAL = {
    "temperature_2m": {"hourly": "temperature_2m", "daily": "temperature_2m_max,temperature_2m_min"},
    "precipitation":  {"hourly": "precipitation",  "daily": "precipitation_sum"},
    "relative_humidity_2m": {"hourly": "relative_humidity_2m", "daily": "relative_humidity_2m_mean"},
    "wind_speed_10m": {"hourly": "wind_speed_10m", "daily": "wind_speed_10m_max"},
    "cloud_cover": {"hourly": "cloud_cover", "daily": "cloud_cover_mean"},
}

ALIASES = {
    "rain": "precipitation",
    "rainfall": "precipitation",
    "humid": "relative_humidity_2m",
    "humidity": "relative_humidity_2m",
    "windy": "wind_speed_10m",
    "cloudy": "cloud_cover",
    "overcast": "cloud_cover",
}

def _canonize(raw: List[str]) -> List[str]:
    out: List[str] = []
    for r in raw:
        k = (r or "").strip().lower()
        k = ALIASES.get(k, k)
        if k not in CANONICAL:
            raise ValueError(f"Unsupported variable: {r}")
        out.append(k)
    return sorted(set(out))

# -------------------- IMPLS (callable from other tools) --------------------

def _pick_variables_impl(query: str) -> Dict[str, Any]:
    want: List[str] = []
    q = (query or "").lower()
    if any(w in q for w in ["rain","precip","shower","storm"]): want.append("precipitation")
    if any(w in q for w in ["humid","humidity","muggy","dry air"]): want.append("relative_humidity_2m")
    if any(w in q for w in ["windy","breezy","gust"]): want.append("wind_speed_10m")
    if any(w in q for w in ["cloud","overcast","clear"]): want.append("cloud_cover")
    if not want or any(w in q for w in ["temp","hot","cold","warmer","cooler","heat"]): want.append("temperature_2m")
    return {"canonical": _canonize(want)}

def _resolve_variables_impl(canonical: List[str], granularity: str) -> Dict[str, Any]:
    if granularity not in ("hourly","daily"):
        raise ValueError("granularity must be 'hourly' or 'daily'")
    hourly_list: List[str] = []
    daily_list:  List[str] = []
    for v in canonical:
        mapping = CANONICAL[v][granularity]
        if granularity == "hourly":
            # Hard guard: hourly cannot request daily sums/aggregates
            if "sum" in mapping:
                raise ValueError(f"Variable '{v}' cannot be requested hourly as a daily sum.")
            hourly_list.append(mapping)
        else:
            daily_list.append(mapping)
    merged = ",".join(hourly_list if granularity=="hourly" else daily_list)
    return {"granularity": granularity, "api_param": merged}

# -------------------- TOOL SHIMS (what the agent invokes) ------------------

@FunctionTool
def pick_variables(query: str) -> Dict[str, Any]:
    return _pick_variables_impl(query)

@FunctionTool
def resolve_variables(canonical: List[str], granularity: str) -> Dict[str, Any]:
    return _resolve_variables_impl(canonical, granularity)

