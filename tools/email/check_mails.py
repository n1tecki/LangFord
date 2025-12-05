from smolagents import tool
from typing import Dict, Any, List, Union
from datetime import datetime, timedelta, timezone
import requests
from tools.email.get_graph_token import _get_ms_access_token


def _to_int_with_default(value: Union[int, str, float], default: int) -> int:
    """Coerce common LLM outputs into an int, with a safe default."""
    try:
        if isinstance(value, str):
            # Extract digits only, e.g. "8 emails" -> 8
            digits = "".join(filter(str.isdigit, value))
            if digits:
                return int(digits)
            return default
        return int(value)
    except Exception:
        return default


@tool
def check_mails(
    max_emails: Union[int, str] = 8,
    days_back: Union[int, str] = 3,
) -> Dict[str, Any]:
    """
    Fetch the most important recent Outlook emails for the signed-in user.

    Use this when the user asks for:
    - a mail brief,
    - important emails,
    - what to respond to first.

    Args:
        max_emails:
            Max number of important emails to return.
        days_back:
            How many days in the past to look.

    Returns:
        dict:
          {
            "total_checked": int,
            "total_returned": int,
            "emails": [...],
            "error": optional str
          }
        Each email:
          {
            "subject": str,
            "sender_name": str,
            "sender_address": str,
            "receivedDateTime": str,
            "importance": "low"|"normal"|"high",
            "isRead": bool,
            "inferenceClassification": "focused"|"other"|None,
            "preview": str,
            "webLink": str,
            "score": int
          }
    """
    max_emails_int = _to_int_with_default(max_emails, default=8)
    days_back_int = _to_int_with_default(days_back, default=3)

    access_token = _get_ms_access_token()

    url = "https://graph.microsoft.com/v1.0/me/messages"
    params = {
        # Grab a reasonable batch and then score/filter in Python
        "$top": "50",
        "$orderby": "receivedDateTime desc",
        "$select": (
            "subject,from,receivedDateTime,importance,"
            "isRead,inferenceClassification,bodyPreview,webLink"
        ),
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        # Keep output structure, but signal error
        return {
            "total_checked": 0,
            "total_returned": 0,
            "emails": [],
            "error": f"Failed to fetch emails: {str(e)}",
        }

    messages: List[Dict[str, Any]] = data.get("value", [])
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days_back_int)

    def parse_dt(dt_str: str) -> datetime:
        # Graph returns ISO 8601, e.g. "2025-11-18T13:08:00Z"
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

    def score_message(msg: Dict[str, Any]) -> int:
        s = 0
        if msg.get("importance") == "high":
            s += 3
        if msg.get("inferenceClassification") == "focused":
            s += 2
        if not msg.get("isRead", True):
            s += 1
        return s

    important: List[Dict[str, Any]] = []
    for msg in messages:
        received_str = msg.get("receivedDateTime")
        if not received_str:
            continue

        try:
            received_dt = parse_dt(received_str)
        except Exception:
            continue

        if received_dt < cutoff:
            continue

        s = score_message(msg)
        if s <= 0:
            # Ignore totally unremarkable, old, read, low-importance stuff
            continue

        sender = (msg.get("from") or {}).get("emailAddress") or {}
        important.append(
            {
                "subject": msg.get("subject"),
                "sender_name": sender.get("name"),
                "sender_address": sender.get("address"),
                "receivedDateTime": received_str,
                "importance": msg.get("importance"),
                "isRead": msg.get("isRead"),
                "inferenceClassification": msg.get("inferenceClassification"),
                "preview": msg.get("bodyPreview"),
                "webLink": msg.get("webLink"),
                "score": s,
            }
        )

    # Sort: score desc, then newest first
    important.sort(
        key=lambda m: (
            -m["score"],
            m["receivedDateTime"] or "",
        )
    )

    selected = important[:max_emails_int]

    return {
        "total_checked": len(messages),
        "total_returned": len(selected),
        "emails": selected,
    }
