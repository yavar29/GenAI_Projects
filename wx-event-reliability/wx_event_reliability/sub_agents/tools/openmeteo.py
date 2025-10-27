from __future__ import annotations
from typing import Dict, Any, List
import requests
import datetime as _dt
from google.adk.tools import FunctionTool

# Import the *impl* (pure helper), not the tool, to avoid tool->tool calls
try:
    from .variables import _resolve_variables_impl
except Exception:
    from variables import _resolve_variables_impl

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ERA5_URL     = "https://archive-api.open-meteo.com/v1/archive"

def _strict_map(canonical: List[str], granularity: str) -> str:
    """Strict canonical→API param mapping (raises on hourly/daily mismatches)."""
    res = _resolve_variables_impl(canonical, granularity)
    return res["api_param"]

def _get(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        r = requests.get(url, params=params, timeout=30)
        payload = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        return {"status": r.status_code, "url": r.url, "payload": payload}
    except Exception as e:
        return {"status": 599, "url": f"{url}?<params>", "payload": {"error": str(e)}}

@FunctionTool
def fetch_openmeteo(
    lat: float,
    lon: float,
    # Let the LLM decide the scenario via time_mode:
    #   "current"          → current weather now (optionally with an hourly context stream)
    #   "hindcast_recent"  → recent past using ?past_days (MUST be ≤5)
    #   "archive_2021"     → older dates via ERA5 (dates must be inside 2021)
    time_mode: str,
    # Variables are canonical names (e.g., "temperature_2m", "precipitation", "wind_speed_10m", ...)
    canonical_variables: List[str],
    # "hourly" or "daily" depending on what the LLM wants to analyze/return
    granularity: str = "hourly",
    # For hindcast_recent (recommended): number of days back from *today*, inclusive (1..5)
    lookback_days: int = 0,
    # For archive_2021 (required): explicit window (must be within 2021)
    start_date: str = "",
    end_date: str = "",
    # Optional: timezone hint. If empty -> UTC for hourly, auto for daily/current
    timezone: str = "",
) -> Dict[str, Any]:
    """
    Minimal, opinionated router to Open-Meteo endpoints.

    Rules:
      1) time_mode == "current"
         → GET /v1/forecast with current=<vars> and (optionally) hourly=<vars> for context.
      2) time_mode == "hindcast_recent" and lookback_days ∈ [1..5]
         → GET /v1/forecast with past_days=lookback_days and hourly|daily=<vars>.
      3) time_mode == "archive_2021"
         → GET /v1/archive with start_date/end_date and hourly|daily=<vars>. Dates must be fully in 2021.

    Strictness:
      - Prevents hourly/daily mismatches (e.g., no "hourly=precipitation_sum").
      - If inputs violate these rules, returns {"error": "..."} with no network call.

    Returns:
      {
        "payload": <Open-Meteo JSON>,
        "request": { ... echoed inputs & resolved params ... },
        "api_urls": ["<full url>"]
      }
    """
    # ---- Normalize
    lat = float(lat); lon = float(lon)
    time_mode = (time_mode or "").strip().lower()
    granularity = (granularity or "hourly").strip().lower()
    tz = timezone.strip() or ("UTC" if granularity == "hourly" else "auto")

    # ---- Strict variable mapping (raises if mismatched)
    try:
        api_param = _strict_map(canonical_variables, granularity)
    except Exception as e:
        return {"error": f"Variable mapping error: {e}"}

    # ---- Build by scenario
    api_urls: List[str] = []
    req_meta: Dict[str, Any] = {
            "time_mode": time_mode,
        "lat": lat, "lon": lon,
        "granularity": granularity,
        "variables": canonical_variables,
        "resolved_param": api_param,
        "timezone": tz,
    }

    if time_mode == "current":
        # Example target:
        # /v1/forecast?latitude=..&longitude=..&current=temperature_2m,...&hourly=temperature_2m,...
        # Keep 'current' subset to variables that are typically supported as current values.
        CURRENT_OK = {
            "temperature_2m", "wind_speed_10m", "relative_humidity_2m",
            "cloud_cover", "precipitation"
        }
        current_vars = [v for v in canonical_variables if v in CURRENT_OK]
        params: Dict[str, Any] = {
            "latitude": lat, "longitude": lon,
            "timezone": "auto",  # current is local by nature
        }
        if current_vars:
            params["current"] = ",".join(current_vars)
        # Optional hourly context stream with same vars (strict-mapped)
        params["hourly"] = api_param if granularity == "hourly" else None
        # prune None
        params = {k: v for k, v in params.items() if v}

        got = _get(FORECAST_URL, params)
        api_urls.append(got["url"])
        if got["status"] != 200:
            return {"error": f"Open-Meteo error {got['status']}", "api_urls": api_urls, "request": req_meta}
        return {"payload": got["payload"], "request": req_meta, "api_urls": api_urls}

    elif time_mode == "hindcast_recent":
        # Must be 1..5 days
        if not (1 <= int(lookback_days) <= 5):
            return {"error": "hindcast_recent requires lookback_days in [1..5]. Use archive_2021 for older dates."}
        params: Dict[str, Any] = {
            "latitude": lat, "longitude": lon,
            "past_days": int(lookback_days),
            "timezone": tz,
        }
        if granularity == "hourly":
            params["hourly"] = api_param
        else:
            params["daily"] = api_param

        got = _get(FORECAST_URL, params)
        api_urls.append(got["url"])
        if got["status"] != 200:
            return {"error": f"Open-Meteo error {got['status']}", "api_urls": api_urls, "request": req_meta}
        # Record the effective window for display convenience
        today = _dt.date.today()
        s_eff = (today - _dt.timedelta(days=int(lookback_days) - 1)).isoformat()
        e_eff = today.isoformat()
        req_meta.update({"start_date": s_eff, "end_date": e_eff, "past_days": int(lookback_days)})
        return {"payload": got["payload"], "request": req_meta, "api_urls": api_urls}

    elif time_mode == "archive_2021":
        # Must provide explicit 2021 window
        if not (start_date and end_date):
            return {"error": "archive_2021 requires start_date and end_date (YYYY-MM-DD)."}
        try:
            s = _dt.date.fromisoformat(start_date)
            e = _dt.date.fromisoformat(end_date)
        except Exception:
            return {"error": "Invalid start_date/end_date; expected YYYY-MM-DD."}
        if not (s.year == 2021 and e.year == 2021 and s <= e):
            return {"error": "Only dates fully inside 2021 are supported for ERA5 in this app."}

        params: Dict[str, Any] = {
            "latitude": lat, "longitude": lon,
            "start_date": s.isoformat(), "end_date": e.isoformat(),
            "timezone": tz,
        }
        if granularity == "hourly":
            params["hourly"] = api_param
        else:
            params["daily"] = api_param

        got = _get(ERA5_URL, params)
        api_urls.append(got["url"])
        if got["status"] != 200:
            return {"error": f"Open-Meteo error {got['status']}", "api_urls": api_urls, "request": req_meta}
        req_meta.update({"start_date": s.isoformat(), "end_date": e.isoformat()})
        return {"payload": got["payload"], "request": req_meta, "api_urls": api_urls}

    else:
        # Keep it explicit: we only support the three scenarios you described.
        return {"error": "Unsupported time_mode. Use one of: 'current', 'hindcast_recent', 'archive_2021'."}

