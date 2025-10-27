# geocode.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple
import re
import requests
from timezonefinder import TimezoneFinder
from google.adk.tools import FunctionTool

_IATA_RE = re.compile(r"^[A-Z]{3}$")
_LATLON_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")

US_STATES = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado",
    "CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho",
    "IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana",
    "ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi",
    "MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey",
    "NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio",
    "OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina",
    "SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia",
    "WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming","DC":"District of Columbia"
}
US_STATE_NAMES = {v.lower(): k for k, v in US_STATES.items()}

def _tz_from_latlon(lat: float, lon: float) -> str | None:
    try:
        tf = TimezoneFinder()
        return tf.timezone_at(lat=lat, lng=lon)
    except Exception:
        return None

def _parse_latlon(query: str) -> Tuple[float, float] | None:
    m = _LATLON_RE.match(query)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None

def _iata_guess(query: str) -> Tuple[float, float] | None:
    # You can extend this small table or wire to an IATA db if you want
    IATA_SMALL = {
        "SJC": (37.3639, -121.9289),  # San Jose
        "BUF": (42.9405, -78.7322),   # Buffalo
        "SEA": (47.4489, -122.3094),  # Seattle
    }
    if _IATA_RE.match(query):
        return IATA_SMALL.get(query.upper())
    return None

def _extract_hints(q: str) -> Dict[str, str | None]:
    qlow = q.lower()
    # find US state hints
    state_code = None
    state_name = None
    tokens = re.split(r"[,;]\s*|\s+", qlow)
    for t in tokens:
        tt = t.strip().upper()
        if tt in US_STATES:
            state_code = tt
            break
    if not state_code:
        for name in US_STATE_NAMES:
            if name in qlow:
                state_name = name
                state_code = US_STATE_NAMES[name]
                break
    # country hint
    country = None
    if " usa" in " " + qlow or " united states" in qlow or (state_code is not None):
        country = "United States"
    elif " india" in qlow: country = "India"
    elif " canada" in qlow: country = "Canada"
    elif " costa rica" in qlow: country = "Costa Rica"
    return {"state_code": state_code, "country": country}

def _score(candidate: Dict[str, Any], q: str, hints: Dict[str, str | None]) -> float:
    score = 0.0
    qname = q.split(",")[0].strip().lower()
    name = str(candidate.get("name","")).lower()
    admin1 = str(candidate.get("admin1","")).lower()
    country = str(candidate.get("country",""))
    pop = float(candidate.get("population", 0) or 0)

    # exact name match
    if qname and qname == name: score += 3.0
    # country hint
    if hints.get("country") and hints["country"] == country: score += 2.0
    # US state hint
    sc = hints.get("state_code")
    if sc:
        if admin1 and admin1.lower() == US_STATES[sc].lower():
            score += 3.0
    # prefer bigger cities a bit
    score += min(pop, 2_000_000) / 2_000_000.0  # 0..1
    return score

def _format_name(c: Dict[str, Any]) -> str:
    p = [c.get("name")]
    if c.get("admin1"): p.append(c["admin1"])
    if c.get("country"): p.append(c["country"])
    return ", ".join([x for x in p if x])

@FunctionTool
def geocode_place(query: str) -> Dict[str, Any]:
    q = query.strip()
    # 1) direct lat,lon
    ll = _parse_latlon(q)
    if ll:
        lat, lon = ll
        tz = _tz_from_latlon(lat, lon) or "UTC"
        return {"name": f"{lat:.4f},{lon:.4f}", "lat": lat, "lon": lon, "country": "", "tz": tz}

    # 2) IATA guess (tiny)
    iata = _iata_guess(q)
    if iata:
        lat, lon = iata
        tz = _tz_from_latlon(lat, lon) or "UTC"
        return {"name": q.upper(), "lat": lat, "lon": lon, "country": "", "tz": tz}

    # 3) Open-Meteo geocoding (disambiguate)
    url = "https://geocoding-api.open-meteo.com/v1/search"
    r = requests.get(url, params={"name": q, "count": 10, "language": "en", "format": "json"}, timeout=20)
    if r.status_code != 200:
        return {"error": f"Geocoding service error ({r.status_code}). Please try again."}
    data = r.json() or {}
    results: List[Dict[str, Any]] = data.get("results") or []
    if not results:
        return {"error": f"Could not geocode '{query}'. Please specify 'City, State, Country' or lat,lon."}

    hints = _extract_hints(q)
    scored = sorted(
        [(c, _score(c, q, hints)) for c in results],
        key=lambda x: x[1],
        reverse=True
    )
    best, best_score = scored[0]
    lat, lon = float(best["latitude"]), float(best["longitude"])
    tz = _tz_from_latlon(lat, lon) or "UTC"

    # disclosure + alternates
    alts = []
    for c, s in scored[1:4]:
        alts.append(_format_name(c))
    warning = None
    if len(results) > 1:
        warning = f"Multiple matches; chose '{_format_name(best)}'. Alternatives: {', '.join(alts)}."

    return {
        "name": _format_name(best),
        "lat": lat,
        "lon": lon,
        "country": best.get("country","") or "",
        "tz": tz,
        "warning": warning,
        "candidates": [ _format_name(c) for c,_ in scored[:5] ]
    }
