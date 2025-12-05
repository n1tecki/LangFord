from smolagents import tool
from datetime import datetime, timedelta, timezone
import requests
from typing import List, Dict, Optional, Union, Any
from tools.calendar.google_token import _get_access_token


def _normalize_date_input(raw: Union[str, Dict[str, Any], None]) -> Optional[str]:
    """
    Normalize various date-like inputs into 'YYYY-MM-DD' string.

    Accepts:
    - simple string: '2025-12-05' or '2025-12-05T14:00:00'
    - dicts from other tools, e.g. {'date': '2025-12-05'} or
      {'iso_datetime': '2025-12-05T14:00:00+01:00'}
    """
    if raw is None:
        return None

    if isinstance(raw, dict):
        for key in ("date", "iso_datetime", "datetime", "iso"):
            val = raw.get(key)
            if isinstance(val, str) and val.strip():
                raw = val
                break
        else:
            # No usable key found
            return None
    else:
        raw = str(raw)

    raw = raw.strip()
    if not raw:
        return None

    # If it's a full datetime, keep only the date part
    if "T" in raw:
        raw = raw.split("T", 1)[0]

    return raw


@tool
def check_events(
    date: Union[str, Dict[str, Any]],
    end_date: Optional[Union[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Read events from Google Calendar.

    Use this only when the user asks to:
    - check availability
    - see their schedule
    - see what is already on the calendar.

    Args:
        date:
            Start date or datetime. Prefer "YYYY-MM-DD".
            Can also be a dict from a date tool with keys like "date" or "iso_datetime".
        end_date:
            Optional end date. Same formats as `date`.
            If omitted, only events on `date` are returned.
            If provided, events from `date` to `end_date` (inclusive) are returned.

    Returns:
        A list of event dicts:
          {
            "id": str,
            "summary": str,
            "start": str,   # ISO or date
            "end": str,     # ISO or date
            "weekday": str | None
          }
        If something goes wrong, returns a single item:
          [{"error": "..."}]
    """
    access_token, CALENDAR_ID = _get_access_token()

    start_str = _normalize_date_input(date)
    end_str = _normalize_date_input(end_date) if end_date is not None else None

    if not start_str:
        return [{"error": "Invalid or empty start date", "raw_input": str(date)}]

    try:
        start_dt = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
    except Exception as e:
        return [
            {
                "error": f"Could not parse start date: {e}",
                "raw_date": start_str,
            }
        ]

    if end_str:
        try:
            end_dt = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc)
        except Exception as e:
            return [
                {
                    "error": f"Could not parse end date: {e}",
                    "raw_end_date": end_str,
                }
            ]
        # inclusive range → add one day for timeMax
        end_dt = end_dt + timedelta(days=1)
    else:
        # Single day: [start, start+1)
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

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        events = response.json().get("items", [])
    except Exception as e:
        return [{"error": f"Failed to fetch events: {str(e)}"}]

    result: List[Dict[str, Any]] = []
    for e in events:
        start = e.get("start", {})
        end = e.get("end", {})

        start_raw = start.get("dateTime") or start.get("date")
        end_raw = end.get("dateTime") or end.get("date")
        weekday: Optional[str] = None

        if start_raw:
            try:
                weekday = datetime.fromisoformat(
                    start_raw.replace("Z", "+00:00")
                ).strftime("%A")
            except Exception:
                weekday = None

        result.append(
            {
                "id": e.get("id"),
                "summary": e.get("summary"),
                "start": start_raw,
                "end": end_raw,
                "weekday": weekday,
            }
        )

    return result
