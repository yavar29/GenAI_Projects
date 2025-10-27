from __future__ import annotations
from typing import Dict, Any, List
from statistics import mean
from google.adk.tools import FunctionTool

def _series_block(data: Dict[str, Any]) -> tuple[str, Dict[str, List[Any]]]:
    if "hourly" in data and data["hourly"]:
        return "hourly", data["hourly"]
    if "daily" in data and data["daily"]:
        return "daily", data["daily"]
    return "none", {}

def _fmt_units(var: str, units: Dict[str, str]) -> str:
    u = units.get(var) or units.get(var.replace("_", "-")) or ""
    return f" {u}" if u else ""

@FunctionTool
def summarise_weather(user_query: str, openmeteo_response: Dict[str, Any], tz: str = "") -> Dict[str, Any]:
    """
    Build a concise, unit-aware answer. Handles hourly/daily blocks, threshold tests, and basic stats.
    Returns: {"final_answer": str}
    """
    if "error" in openmeteo_response:
        return {"final_answer": openmeteo_response["error"]}

    params = openmeteo_response.get("params", {})
    data = openmeteo_response.get("data", {})
    units = openmeteo_response.get("units", {}) or {}
    key, block = _series_block(data)

    if key == "none" or not block:
        return {"final_answer": "No weather data was available for that date/location."}

    # Choose primary variable = first non-time key
    var_names = [k for k in block.keys() if k != "time"]
    if not var_names:
        return {"final_answer": "No variables returned."}
    primary = var_names[0]

    times = block.get("time", [])
    vals = block.get(primary, [])

    if not vals:
        return {"final_answer": f"No data for {primary} on the requested window."}

    # Basic stats
    try:
        vals_num = [float(v) for v in vals]
        vmin, vmax, vmean = min(vals_num), max(vals_num), mean(vals_num)
    except Exception:
        vmin = vmax = vmean = None

    unit = _fmt_units(primary, units)
    sdate, edate = params.get("start_date"), params.get("end_date")
    tz_note = f" (local: {tz})" if tz else ""

    # Threshold parsing (lightweight detection in case pick_variables already flagged it)
    # We keep the message simple and rely on variables tool for complex ops.
    result_bits = []
    if vmin is not None and vmax is not None:
        if key == "hourly":
            result_bits.append(f"{primary} ranged {vmin:.2f}–{vmax:.2f}{unit}")
        else:
            # daily: report per-day min/max across window
            result_bits.append(f"{primary} across {sdate}..{edate} had min {vmin:.2f}{unit}, max {vmax:.2f}{unit}")
    if vmean is not None:
        result_bits.append(f"mean {vmean:.2f}{unit}")

    core = "; ".join(result_bits) if result_bits else f"Found {len(vals)} points for {primary}{unit}"
    answer = (
        f"{core}. Window: {sdate}..{edate} UTC{tz_note}."
    )

    return {"final_answer": answer}


