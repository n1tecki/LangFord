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
    Turn a natural-language date/time expression into a concrete datetime.

    Use this tool whenever the user uses fuzzy time phrases like:
    - "tomorrow at 3pm"
    - "next Friday"
    - "Friday in two weeks"
    - "this afternoon"

    The calling agent should:
    - call this tool first,
    - then pass the returned "iso_datetime" or "date" into calendar tools,
    - never invent dates/times by itself.

    Args:
        expression:
            Natural language date expression as stated by the user.
        now_iso:
            Optional reference datetime (ISO-8601). If omitted, uses "now" in `timezone`.
        timezone:
            IANA timezone, e.g. "Europe/Vienna".

    Returns:
        dict with:
            - "ok": bool (True if parsing succeeded)
            - "iso_datetime": str (full ISO-8601, only if ok=True)
            - "date": str ("YYYY-MM-DD", only if ok=True)
            - "time": str ("HH:MM", 24h, only if ok=True)
            - "timezone": str
            - "original_expression": str
            - "error": str (only if ok=False)
    """
    # Basic validation
    if not expression or not str(expression).strip():
        return {
            "ok": False,
            "error": "empty_expression",
            "original_expression": expression,
            "timezone": timezone,
        }

    expression_str = str(expression).strip()

    # Determine reference "now"
    try:
        tz = ZoneInfo(timezone)
    except Exception as exc:
        return {
            "ok": False,
            "error": f"invalid_timezone: {exc}",
            "original_expression": expression_str,
            "timezone": timezone,
        }

    try:
        if now_iso:
            base_dt = datetime.fromisoformat(str(now_iso))
            if base_dt.tzinfo is None:
                base_dt = base_dt.replace(tzinfo=tz)
            else:
                base_dt = base_dt.astimezone(tz)
        else:
            base_dt = datetime.now(tz)
    except Exception as exc:
        return {
            "ok": False,
            "error": f"invalid_now_iso: {exc}",
            "original_expression": expression_str,
            "timezone": timezone,
        }

    # Parse with dateparser
    parsed = dateparser.parse(
        expression_str,
        settings={
            "RELATIVE_BASE": base_dt,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "TIMEZONE": timezone,
            "PREFER_DATES_FROM": "future",
        },
    )

    if parsed is None:
        return {
            "ok": False,
            "error": "could_not_parse",
            "original_expression": expression_str,
            "timezone": timezone,
        }

    # Normalize to target timezone
    try:
        parsed = parsed.astimezone(tz)
    except Exception:
        parsed = parsed  # best effort; should already be TZ-aware

    iso_dt = parsed.isoformat(timespec="seconds")
    date_str = parsed.date().isoformat()
    time_str = parsed.strftime("%H:%M")

    return {
        "ok": True,
        "iso_datetime": iso_dt,
        "date": date_str,
        "time": time_str,
        "timezone": timezone,
        "original_expression": expression_str,
    }
