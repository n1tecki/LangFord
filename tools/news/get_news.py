from smolagents import tool
from typing import Optional, Dict, Any, List, Union
import requests
import xml.etree.ElementTree as ET
import trafilatura
from dotenv import load_dotenv
import os

load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")


def _fetch_google_news_rss(num: int = 5) -> List[Dict[str, Any]]:
    """Fetch general news from Google News RSS feed."""
    url = "https://news.google.com/rss"
    r = requests.get(url, timeout=30)
    r.raise_for_status()

    root = ET.fromstring(r.content)
    items = root.findall(".//item")

    results: List[Dict[str, Any]] = []
    for item in items[:num]:
        title = item.find("title")
        link = item.find("link")
        pub_date = item.find("pubDate")
        source = item.find("source")

        results.append(
            {
                "title": title.text if title is not None else "No title",
                "link": link.text if link is not None else "",
                "pub_date": pub_date.text if pub_date is not None else "No date",
                "source": source.text if source is not None else "Google News",
            }
        )
    return results


def _serper_news_search(query: str, num: int = 5) -> List[Dict[str, Any]]:
    """Fetch news for a specific topic or query via Serper."""
    if not SERPER_API_KEY:
        raise ValueError("SERPER_API_KEY env var is not set.")

    url = "https://google.serper.dev/news"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": query, "gl": "us", "hl": "en", "tbs": "qdr:d"}
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()

    results: List[Dict[str, Any]] = []
    for item in data.get("news", [])[:num]:
        results.append(
            {
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet"),
                "date": item.get("date"),
                "source": item.get("source"),
            }
        )
    return results


def _serper_site_search(query: str, site: str, num: int = 5) -> List[Dict[str, Any]]:
    """Site restricted web search via Serper."""
    if not SERPER_API_KEY:
        raise ValueError("SERPER_API_KEY env var is not set.")

    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": f"site:{site} {query}", "gl": "us", "hl": "en"}
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()

    results: List[Dict[str, Any]] = []
    for item in data.get("organic", [])[:num]:
        results.append(
            {
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet"),
                "favicons": item.get("favicons", {}),
            }
        )
    return results


def _fetch_article(url: str, max_chars: int = 12000) -> Dict[str, Any]:
    """Fetch and extract clean article text with trafilatura."""
    downloaded = trafilatura.fetch_url(url, timeout=30)
    text = (
        trafilatura.extract(downloaded, include_comments=False) if downloaded else None
    )
    if not text:
        return {"ok": False, "error": "could_not_extract"}

    text = text.strip()
    if len(text) > max_chars:
        text = text[:max_chars] + " ..."
    return {"ok": True, "text": text}


@tool
def news_report(
    query: Optional[str] = None,
    location: Optional[str] = "Vienna, Austria",
    url: Optional[str] = None,
    world_num: Union[int, str] = 5,
    local_num: Union[int, str] = 5,
    max_chars: Union[int, str] = 12000,
    as_article: Union[bool, str] = False,
) -> Dict[str, Any]:
    """
    High-level news and article reporting tool.

    Use this tool **at most once per user request**.

    - For "what's the news today": call with default arguments.
      Returns a daily brief: world + local headlines.
    - For topic-specific news: pass `query="..."`.
    - For "explain this article" when you only know the title or topic:
      pass `query="title or close text", as_article=True`.
      The tool will search for the article, fetch it, and return the text.
    - For a specific article URL: pass `url="..."`.

    Args:
        query:
            Topic / article title / search keywords.
        location:
            City / country to get local headlines for.
        url:
            Article URL to fetch and analyze.
        world_num:
            Number of world headlines for daily brief.
        local_num:
            Number of local headlines for daily brief.
        max_chars:
            Max characters to extract from article text.
        as_article:
            If True and `query` is provided, search for the best-matching
            article and return its full text (mode="article").

    Returns:
        dict with one of the modes:
        - "daily_brief": world + local headlines
        - "news_search": topic-based news
        - "article": extracted article text (+ matched title/url)
        - plus optional "errors"/"error" fields instead of raising.
    """

    # --- Lenient argument handling (same style as check_mails) ---
    # world_num
    try:
        if isinstance(world_num, str):
            digits = "".join(filter(str.isdigit, world_num))
            world_num_int = int(digits) if digits else 5
        else:
            world_num_int = int(world_num)
    except Exception:
        world_num_int = 5

    # local_num
    try:
        if isinstance(local_num, str):
            digits = "".join(filter(str.isdigit, local_num))
            local_num_int = int(digits) if digits else 5
        else:
            local_num_int = int(local_num)
    except Exception:
        local_num_int = 5

    # max_chars
    try:
        if isinstance(max_chars, str):
            digits = "".join(filter(str.isdigit, max_chars))
            max_chars_int = int(digits) if digits else 12000
        else:
            max_chars_int = int(max_chars)
    except Exception:
        max_chars_int = 12000

    # as_article (accept "true"/"false"/"1"/"0" etc)
    if isinstance(as_article, str):
        as_article_norm = as_article.strip().lower() in {
            "true",
            "1",
            "yes",
            "y",
            "on",
        }
    else:
        as_article_norm = bool(as_article)
    # -------------------------------------------------------------

    # 1) Article mode: explicit URL
    if url:
        try:
            article = _fetch_article(url, max_chars=max_chars_int)
        except Exception as e:
            return {
                "mode": "article",
                "url": url,
                "article": {"ok": False, "error": f"fetch_failed: {str(e)}"},
            }

        return {
            "mode": "article",
            "url": url,
            "article": article,
        }

    # 2) Article mode from title / query
    if query and as_article_norm:
        try:
            candidates = _serper_news_search(query=query, num=3)
        except Exception as e:
            return {
                "mode": "article_search_failed",
                "query": query,
                "reason": "serper_error",
                "detail": str(e),
            }

        if not candidates:
            return {
                "mode": "article_search_failed",
                "query": query,
                "reason": "no_results",
            }

        best = candidates[0]  # keep it simple: first result
        link = best.get("link")
        if link:
            try:
                article = _fetch_article(link, max_chars=max_chars_int)
            except Exception as e:
                article = {"ok": False, "error": f"fetch_failed: {str(e)}"}
        else:
            article = {"ok": False, "error": "no_link_in_result"}

        return {
            "mode": "article",
            "query": query,
            "matched_title": best.get("title"),
            "url": link,
            "source": best.get("source"),
            "article": article,
        }

    # 3) Topic-based news search: query only
    if query:
        try:
            items = _serper_news_search(query=query, num=world_num_int)
        except Exception as e:
            return {
                "mode": "news_search",
                "query": query,
                "items": [],
                "error": f"topic_search_failed: {str(e)}",
            }

        return {
            "mode": "news_search",
            "query": query,
            "items": items,
        }

    # 4) Default: daily brief (world + local)
    world: List[Dict[str, Any]] = []
    local: List[Dict[str, Any]] = []
    errors: Dict[str, str] = {}

    try:
        world = _fetch_google_news_rss(num=world_num_int)
    except Exception as e:
        errors["world"] = str(e)

    local_query = f"{location} news" if location else "local news"
    try:
        local = _serper_news_search(query=local_query, num=local_num_int)
    except Exception as e:
        errors["local"] = str(e)

    result: Dict[str, Any] = {
        "mode": "daily_brief",
        "location": location,
        "world": world,
        "local": local,
    }
    if errors:
        result["errors"] = errors

    return result
