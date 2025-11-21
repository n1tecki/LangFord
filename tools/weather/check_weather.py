from smolagents import tool
from typing import Optional, Dict
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


@tool
def get_weather(
    location: str,
    date: str,
    time: Optional[str] = None,
) -> Dict:
    """
    Get Google Weather forecast for a given location and date/time.

    Use this tool when the user asks for weather
    at a specific place and date (time optional).

    Args:
        location (str):
            Free-text location, e.g. "Vienna, Austria".
        date (str):
            Target date in "YYYY-MM-DD".
        time (str, optional):
            Target time in "HH:MM" (24h). If omitted, a
            representative hour on that date is chosen.

    Returns:
        dict: Selected forecast with basic fields:
              location, date, hour, description, temperature,
              precipitationProbabilityPercent, plus latitude/longitude.
    """
    units: str = "METRIC"

    if not WEATHER_API_KEY:
        raise ValueError("GOOGLE_WEATHER_API_KEY env var is not set.")

    # --- 1) Geocode the location ---
    coords = _geocode_location(location)
    lat, lng = coords["lat"], coords["lng"]

    # --- 2) Call Google Weather hourly forecast (up to 240 hours) ---
    weather_url = "https://weather.googleapis.com/v1/forecast/hours:lookup"
    params = {
        "key": WEATHER_API_KEY,
        "location.latitude": lat,
        "location.longitude": lng,
        "hours": 240,  # up to ~10 days ahead
        "pageSize": 240,  # avoid pagination
    }
    if units.upper() == "IMPERIAL":
        params["unitsSystem"] = "IMPERIAL"

    resp = requests.get(weather_url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    hours_list = data.get("forecastHours", [])
    if not hours_list:
        raise ValueError("No forecastHours returned by Weather API.")

    # --- 3) Parse target date/hour ---
    try:
        target_date = datetime.fromisoformat(date).date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date!r}, expected YYYY-MM-DD")

    target_hour: Optional[int] = None
    if time:
        try:
            target_hour = int(time.split(":")[0])
        except ValueError:
            raise ValueError(f"Invalid time format: {time!r}, expected HH:MM")

    # --- 4) Find the closest forecast hour for that date/time ---
    best = None
    best_score = None

    for fh in hours_list:
        dd = fh.get("displayDateTime")
        if not dd:
            continue

        fh_date = Date(dd["year"], dd["month"], dd["day"])
        if fh_date != target_date:
            continue

        fh_hour = dd["hours"]  # local hour at location

        if target_hour is None:
            # pick something "middle of the day"
            score = abs(fh_hour - 12)
        else:
            score = abs(fh_hour - target_hour)

        if best is None or score < best_score:
            best = fh
            best_score = score

    if best is None:
        # Date is probably out of range (> ~10 days ahead)
        raise ValueError(
            f"No hourly forecast found for {date} at {location}. "
            "Weather API typically covers only about 10 days ahead."
        )

    # --- 5) Build a compact return payload ---
    dd = best.get("displayDateTime", {})
    cond = best.get("weatherCondition", {})
    desc = (cond.get("description") or {}).get("text")

    temp = best.get("temperature", {})
    precip_prob = None
    if "precipitation" in best and "probability" in best["precipitation"]:
        precip_prob = best["precipitation"]["probability"].get("percent")

    result = {
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
