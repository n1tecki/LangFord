from smolagents import tool
from datetime import datetime, timedelta, timezone
import requests
from typing import List, Dict, Optional
from tools.calendar.google_token import _get_access_token


@tool
def check_events(
    date: str,
    end_date: Optional[str] = None,
) -> List[Dict]:
    """
    Read events from the calendar.
    Use this tool only when the user asks to check availability, check schedule, or see what is already on the calendar.

    Args:
        date (str):
            Start date in format "YYYY-MM-DD".
        end_date (str, optional):
            End date in format "YYYY-MM-DD". If omitted, only events
            on `date` are returned. If provided, events from `date`
            to `end_date` (inclusive) are returned.

    Returns:
        list: List of event dicts with keys: "summary", "start", "end", "id", "weekday".
    """

    # Fallback to environment variable if token not passed explicitly
    access_token, CALENDAR_ID = _get_access_token()

    # Parse start date
    start_dt = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)

    # If no end_date: single day, else: inclusive range
    if end_date:
        end_dt = datetime.fromisoformat(end_date).replace(
            tzinfo=timezone.utc
        ) + timedelta(days=1)
    else:
        end_dt = start_dt + timedelta(days=1)

    time_min = start_dt.isoformat()
    time_max = end_dt.isoformat()

    url = f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events"
    params = {
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    events = response.json().get("items", [])

    # Normalize output so the agent gets clean, simple fields
    result = []
    for e in events:
        start = e.get("start", {})
        end = e.get("end", {})

        start_raw = start.get("dateTime") or start.get("date")
        weekday: Optional[str] = None
        if start_raw:
            try:
                weekday = datetime.fromisoformat(start_raw).strftime("%A")
            except ValueError:
                # Fallback: ignore weekday if parsing fails
                weekday = None

        result.append(
            {
                "id": e.get("id"),
                "summary": e.get("summary"),
                "start": start_raw,
                "end": end.get("dateTime") or end.get("date"),
                "weekday": weekday,
            }
        )

    return result
