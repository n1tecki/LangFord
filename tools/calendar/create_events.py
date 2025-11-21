from smolagents import tool
from typing import Optional, Dict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # Python 3.9+
import os
import requests
from tools.calendar.google_token import _get_access_token

CALENDAR_TIMEZONE = os.getenv("GOOGLE_CALENDAR_TIMEZONE", "Europe/Vienna")


@tool
def create_events(
    summary: str,
    start_date: str,
    end_date: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    all_day: bool = False,
    duration_minutes: int = 60,
) -> Dict:
    """
    Create a new calendar event.
    Use this tool whenever the user wants to add, schedule, insert, or put an event into their calendar.


    Args:
        summary (str):
            Event title. Example: "Chinese lesson".
        start_date (str):
            Start time, e.g. "2025-11-22T20:00:00".
        end_date (str, optional):
            End time. Same format as start. If omitted:
            - all_day=False → start + duration_minutes
            - all_day=True  → start + 1 day
        description (str, optional):
            Optional event notes.
        location (str, optional):
            Optional location string.
        all_day (boolean):
            True for all-day events (date only).
        duration_minutes (int):
            Duration used when end is omitted. Default: 60.

    Returns:
        dict: Google Calendar event data (id, link, start_date, end_date).
    """

    access_token, CALENDAR_ID = _get_access_token()
    url = f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    if all_day:
        # start is "YYYY-MM-DD"
        start_date = datetime.fromisoformat(start_date).date()

        if end_date is not None:
            end_date = datetime.fromisoformat(end_date).date()
        else:
            end_date = start_date + timedelta(days=1)

        start_payload = {"date": start_date.isoformat()}
        end_payload = {"date": end_date.isoformat()}
    else:
        # start is "YYYY-MM-DDTHH:MM[:SS]" in LOCAL time
        start_dt = datetime.fromisoformat(start_date)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=ZoneInfo(CALENDAR_TIMEZONE))

        if end_date is not None:
            end_dt = datetime.fromisoformat(end_date)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=ZoneInfo(CALENDAR_TIMEZONE))
        else:
            end_dt = start_dt + timedelta(minutes=duration_minutes)

        start_payload = {
            "dateTime": start_dt.isoformat(),
            "timeZone": CALENDAR_TIMEZONE,
        }
        end_payload = {
            "dateTime": end_dt.isoformat(),
            "timeZone": CALENDAR_TIMEZONE,
        }

    body = {
        "summary": summary,
        "start": start_payload,
        "end": end_payload,
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location

    response = requests.post(url, headers=headers, json=body, timeout=10)
    response.raise_for_status()
    event = response.json()

    return {
        "id": event.get("id"),
        "htmlLink": event.get("htmlLink"),
        "summary": event.get("summary"),
        "start": event.get("start", {}).get("dateTime")
        or event.get("start", {}).get("date"),
        "end": event.get("end", {}).get("dateTime") or event.get("end", {}).get("date"),
    }
