from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any
from smolagents import tool

from zoneinfo import ZoneInfo
import dateparser


@tool
def resolve_date_expression(
    expression: str,
    now_iso: Optional[str] = None,
    timezone: str = "Europe/Vienna",
) -> Dict[str, Any]:
    """
    Convert a natural language date/time expression into an absolute ISO-8601 datetime
    in the user's timezone.

    This tool is intended for use by an LLM agent before creating or checking calendar
    events, so the model never has to guess concrete dates for phrases like
    "tomorrow", "next Friday", or "Friday in two weeks".

    Args:
        expression (str): Natural language date expression as stated by the user,
            e.g. "next Friday at 3pm", "tomorrow 14:00", "Friday in two weeks".
        now_iso (str, optional): Reference datetime in ISO-8601 format,
            e.g. "2025-12-01T15:00:00". If omitted, the current time in `timezone`
            is used as the reference point.
        timezone (str, optional): IANA timezone name to interpret the expression in,
            e.g. "Europe/Vienna".

    Returns:
        dict: A JSON-serializable dictionary containing:
            - "iso_datetime" (str): Full ISO-8601 datetime string in the given timezone.
            - "date" (str): Date in "YYYY-MM-DD" format.
            - "time" (str): Time in "HH:MM" (24h) format.
            - "timezone" (str): The timezone used.
            - "original_expression" (str): The original user expression.

        The calling agent should use "iso_datetime" when passing a concrete datetime
        into calendar tools and must not invent or modify the date on its own.

    Raises:
        ValueError: If the expression cannot be parsed into a valid datetime.
    """
    if not expression or not expression.strip():
        raise ValueError("Empty date expression provided.")

    # Determine the reference 'now'
    try:
        if now_iso:
            base_dt = datetime.fromisoformat(now_iso)
            # Ensure it is timezone-aware in the desired timezone
            if base_dt.tzinfo is None:
                base_dt = base_dt.replace(tzinfo=ZoneInfo(timezone))
            else:
                base_dt = base_dt.astimezone(ZoneInfo(timezone))
        else:
            base_dt = datetime.now(ZoneInfo(timezone))
    except Exception as exc:
        raise ValueError(f"Invalid now_iso or timezone: {exc}") from exc

    # Parse using dateparser with the given base datetime and timezone
    parsed = dateparser.parse(
        expression,
        settings={
            "RELATIVE_BASE": base_dt,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "TIMEZONE": timezone,
            "PREFER_DATES_FROM": "future",  # so "Friday" usually means next Friday
        },
    )

    if parsed is None:
        raise ValueError(f"Could not parse date expression: {expression!r}")

    # Normalize to target timezone
    parsed = parsed.astimezone(ZoneInfo(timezone))

    iso_dt = parsed.isoformat(timespec="seconds")
    date_str = parsed.date().isoformat()
    time_str = parsed.strftime("%H:%M")

    return {
        "iso_datetime": iso_dt,
        "date": date_str,
        "time": time_str,
        "timezone": timezone,
        "original_expression": expression,
    }
