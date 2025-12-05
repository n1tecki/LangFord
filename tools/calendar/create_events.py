from smolagents import tool
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # Python 3.9+
import os
import requests
from tools.calendar.google_token import _get_access_token

CALENDAR_TIMEZONE = os.getenv("GOOGLE_CALENDAR_TIMEZONE", "Europe/Vienna")


def _to_bool(value: Union[bool, str, int]) -> bool:
    """Coerce common LLM outputs into a boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y", "on"}
    return bool(value)


def _to_int(value: Union[int, str, float], default: int) -> int:
    """Coerce common LLM outputs into an int with a safe default."""
    try:
        if isinstance(value, str):
            digits = "".join(filter(str.isdigit, value))
            if digits:
                return int(digits)
            return default
        return int(value)
    except Exception:
        return default


def _extract_datetime_str(raw: Union[str, Dict[str, Any]]) -> str:
    """
    Extract a usable datetime string from:
    - plain strings
    - dicts like {'iso_datetime': '...'} or {'dateTime': '...'}.
    """
    if isinstance(raw, dict):
        for key in ("iso_datetime", "dateTime", "datetime", "start", "date"):
            val = raw.get(key)
            if isinstance(val, str) and val.strip():
                raw = val
                break
        else:
            raw = ""

    s = str(raw).strip()
    return s


def _extract_date_str(raw: Union[str, Dict[str, Any]]) -> str:
    """
    Extract a usable date string (YYYY-MM-DD) from various inputs.
    """
    s = _extract_datetime_str(raw)
    if "T" in s:
        s = s.split("T", 1)[0]
    return s


@tool
def create_events(
    summary: str,
    start_date: Union[str, Dict[str, Any]],
    end_date: Optional[Union[str, Dict[str, Any]]] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    all_day: Union[bool, str, int] = False,
    duration_minutes: Union[int, str, float] = 60,
) -> Dict[str, Any]:
    """
    Create a Google Calendar event.

    Use this when the user wants to:
    - add / schedule / book / put something in the calendar.

    The model must always provide at least:
    - summary (title)
    - start_date (date or datetime).

    Args:
        summary:
            Event title. Example: "Chinese lesson".
        start_date:
            Start date or datetime.
            - Timed: "2025-11-22T20:00:00"
            - All-day: "2025-11-22" (or dict from a date tool).
        end_date:
            Optional end date/time. If omitted:
            - all_day=False → start + duration_minutes
            - all_day=True  → start + 1 day (exclusive, as per Google Calendar)
        description:
            Optional event notes.
        location:
            Optional location.
        all_day:
            True for all-day events (date only).
        duration_minutes:
            Used when no explicit end_date is given.

    Returns:
        dict with the created event:
          {
            "id": str,
            "htmlLink": str,
            "summary": str,
            "start": str,
            "end": str
          }
        or:
          {"error": "...", "requested": {...}} on failure.
    """
    all_day_flag = _to_bool(all_day)
    duration_min_int = _to_int(duration_minutes, default=60)

    access_token, CALENDAR_ID = _get_access_token()
    url = f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        if all_day_flag:
            # Normalize to date string "YYYY-MM-DD"
            start_str = _extract_date_str(start_date)
            if not start_str:
                return {
                    "error": "Invalid start_date for all-day event",
                    "raw_start_date": str(start_date),
                }

            start_date_obj = datetime.fromisoformat(start_str).date()

            if end_date is not None:
                end_str = _extract_date_str(end_date)
                if not end_str:
                    return {
                        "error": "Invalid end_date for all-day event",
                        "raw_end_date": str(end_date),
                    }
                end_date_obj = datetime.fromisoformat(end_str).date()
            else:
                # For all-day events, Google expects end = next day
                end_date_obj = start_date_obj + timedelta(days=1)

            start_payload = {"date": start_date_obj.isoformat()}
            end_payload = {"date": end_date_obj.isoformat()}

        else:
            # Timed event
            start_str = _extract_datetime_str(start_date)
            if not start_str:
                return {
                    "error": "Invalid start_date for timed event",
                    "raw_start_date": str(start_date),
                }

            start_dt = datetime.fromisoformat(start_str)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=ZoneInfo(CALENDAR_TIMEZONE))
            else:
                start_dt = start_dt.astimezone(ZoneInfo(CALENDAR_TIMEZONE))

            if end_date is not None:
                end_str = _extract_datetime_str(end_date)
                if not end_str:
                    return {
                        "error": "Invalid end_date for timed event",
                        "raw_end_date": str(end_date),
                    }

                end_dt = datetime.fromisoformat(end_str)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=ZoneInfo(CALENDAR_TIMEZONE))
                else:
                    end_dt = end_dt.astimezone(ZoneInfo(CALENDAR_TIMEZONE))
            else:
                end_dt = start_dt + timedelta(minutes=duration_min_int)

            start_payload = {
                "dateTime": start_dt.isoformat(),
                "timeZone": CALENDAR_TIMEZONE,
            }
            end_payload = {
                "dateTime": end_dt.isoformat(),
                "timeZone": CALENDAR_TIMEZONE,
            }

    except Exception as e:
        return {
            "error": f"Failed to normalize event dates: {str(e)}",
            "raw_start_date": str(start_date),
            "raw_end_date": str(end_date),
        }

    body: Dict[str, Any] = {
        "summary": summary,
        "start": start_payload,
        "end": end_payload,
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location

    try:
        response = requests.post(url, headers=headers, json=body, timeout=10)
        response.raise_for_status()
        event = response.json()
    except Exception as e:
        return {
            "error": f"Failed to create event: {str(e)}",
            "requested": body,
        }

    return {
        "id": event.get("id"),
        "htmlLink": event.get("htmlLink"),
        "summary": event.get("summary"),
        "start": event.get("start", {}).get("dateTime")
        or event.get("start", {}).get("date"),
        "end": event.get("end", {}).get("dateTime")
        or event.get("end", {}).get("date"),
    }
