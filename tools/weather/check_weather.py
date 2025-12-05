from smolagents import tool
from typing import Optional, Dict, Any, Union
from datetime import datetime, date as Date
import requests
from dotenv import load_dotenv
import os

load_dotenv()
WEATHER_API_KEY = os.getenv("GOOGLE_WEATHER_API")


def _geocode_location(location: str) -> Dict[str, float]:
    """
    Resolve a human-readable location to latitude/longitude using
    the Google Geocoding API.
    """
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": location, "key": WEATHER_API_KEY}

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "OK" or not data.get("results"):
        raise ValueError(f"Could not geocode location: {location!r}")

    loc = data["results"][0]["geometry"]["location"]
    return {"lat": loc["lat"], "lng": loc["lng"]}


def _extract_date_str(raw: Union[str, Dict[str, Any]]) -> str:
    """
    Normalize date input into 'YYYY-MM-DD'.

    Accepts:
    - simple string: '2025-12-05' or '2025-12-05T14:00:00'
    - dicts from other tools, e.g.
      {'date': '2025-12-05'} or
      {'iso_datetime': '2025-12-05T14:00:00+01:00'}
    """
    if isinstance(raw, dict):
        for key in ("date", "iso_datetime", "datetime", "iso"):
            val = raw.get(key)
            if isinstance(val, str) and val.strip():
                raw = val
                break
        else:
            raw = ""

    s = str(raw).strip()
    if not s:
        return ""

    if "T" in s:
        s = s.split("T", 1)[0]

    return s


def _extract_hour(raw: Union[str, Dict[str, Any], None]) -> Optional[int]:
    """
    Extract an hour (0-23) from:
    - "HH:MM"
    - "2025-12-05T14:30:00"
    - dicts with 'time' or 'iso_datetime'.
    """
    if raw is None:
        return None

    if isinstance(raw, dict):
        for key in ("time", "iso_datetime", "datetime", "iso"):
            val = raw.get(key)
            if isinstance(val, str) and val.strip():
                raw = val
                break
        else:
            raw = ""

    s = str(raw).strip()
    if not s:
        return None

    # If full datetime, take part after 'T'
    if "T" in s:
        s = s.split("T", 1)[1]

    # Now expect "HH:MM[:SS]"
    try:
        hour_str = s.split(":", 1)[0]
        return int(hour_str)
    except Exception:
        return None


@tool
def get_weather(
    location: str,
    date: Union[str, Dict[str, Any]],
    time: Optional[Union[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Get Google Weather forecast for a given place and date/time.

    Use this when the user asks:
    - "weather in X tomorrow",
    - "weather in X on Friday at 15:00", etc.

    Args:
        location:
            Free-text location, e.g. "Vienna, Austria".
        date:
            Target date (or datetime). Prefer "YYYY-MM-DD".
            Can also be a dict from a date tool.
        time:
            Optional time (or datetime/dict). If omitted, a "middle of day"
            hour is chosen for that date.

    Returns:
        dict with:
          - "location", "latitude", "longitude"
          - "date", "hour", "utcOffset"
          - "description", "icon"
          - "temperature", "temperatureUnit"
          - "precipitationProbabilityPercent"
        or:
          {"error": "..."} if something goes wrong.
    """
    units: str = "METRIC"

    if not WEATHER_API_KEY:
        return {"error": "GOOGLE_WEATHER_API env var is not set."}

    # --- 1) Normalize date/time input ---
    date_str = _extract_date_str(date)
    if not date_str:
        return {"error": "Invalid or empty date input.", "raw_date": str(date)}

    try:
        target_date = datetime.fromisoformat(date_str).date()
    except Exception as e:
        return {
            "error": f"Invalid date format: {date_str!r}, expected YYYY-MM-DD",
            "detail": str(e),
        }

    target_hour = _extract_hour(time)

    # --- 2) Geocode the location ---
    try:
        coords = _geocode_location(location)
    except Exception as e:
        return {
            "error": f"Failed to geocode location: {str(e)}",
            "location": location,
        }

    lat, lng = coords["lat"], coords["lng"]

    # --- 3) Call Google Weather hourly forecast ---
    weather_url = "https://weather.googleapis.com/v1/forecast/hours:lookup"
    params = {
        "key": WEATHER_API_KEY,
        "location.latitude": lat,
        "location.longitude": lng,
        "hours": 240,      # up to ~10 days ahead
        "pageSize": 240,   # avoid pagination
    }
    if units.upper() == "IMPERIAL":
        params["unitsSystem"] = "IMPERIAL"

    try:
        resp = requests.get(weather_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {
            "error": f"Failed to fetch weather data: {str(e)}",
            "location": location,
        }

    hours_list = data.get("forecastHours", [])
    if not hours_list:
        return {
            "error": "No forecastHours returned by Weather API.",
            "location": location,
        }

    # --- 4) Find the closest forecast hour for that date/time ---
    best = None
    best_score: Optional[int] = None

    for fh in hours_list:
        dd = fh.get("displayDateTime")
        if not dd:
            continue

        fh_date = Date(dd["year"], dd["month"], dd["day"])
        if fh_date != target_date:
            continue

        fh_hour = dd.get("hours")
        if fh_hour is None:
            continue

        if target_hour is None:
            # Middle of the day if no specific time requested
            score = abs(fh_hour - 12)
        else:
            score = abs(fh_hour - target_hour)

        if best is None or best_score is None or score < best_score:
            best = fh
            best_score = score

    if best is None:
        return {
            "error": (
                f"No hourly forecast found for {date_str} at {location}. "
                "Weather API typically covers only ~10 days ahead."
            ),
            "location": location,
            "date": date_str,
        }

    # --- 5) Build a compact return payload ---
    dd = best.get("displayDateTime", {})
    cond = best.get("weatherCondition", {})
    desc = (cond.get("description") or {}).get("text")

    temp = best.get("temperature", {})
    precip_prob = None
    if "precipitation" in best and "probability" in best["precipitation"]:
        precip_prob = best["precipitation"]["probability"].get("percent")

    result: Dict[str, Any] = {
        "location": location,
        "latitude": lat,
        "longitude": lng,
        "date": f"{dd.get('year', target_date.year):04d}-"
        f"{dd.get('month', target_date.month):02d}-"
        f"{dd.get('day', target_date.day):02d}",
        "hour": dd.get("hours"),
        "utcOffset": dd.get("utcOffset"),
        "description": desc,
        "icon": cond.get("iconBaseUri"),
        "temperature": temp.get("degrees"),
        "temperatureUnit": temp.get("unit"),
        "precipitationProbabilityPercent": precip_prob,
    }

    return result
