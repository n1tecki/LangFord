import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict, Any

from smolagents import tool

URL = "https://finviz.com/news.ashx"

# Matches either:
#  - "08:06AM"
#  - "Nov-20"
TS_RE = re.compile(
    r"(?P<ts>(\d{1,2}:\d{2}[AP]M|[A-Z][a-z]{2}-\d{2}))\s+(?P<title>.+?)\s+\S+$"
)

def _scrape_finviz_news() -> List[Dict[str, Any]]:
    """Low-level HTML scraper, returns raw items (no slicing)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    resp = requests.get(URL, headers=headers, timeout=15)
    resp.raise_for_status()

    html = resp.text

    # --- 1) Detect if Cloudflare / JS challenge instead of real content ---
    lower_html = html.lower()
    if "cloudflare" in lower_html and (
        "attention required" in lower_html or "please enable javascript" in lower_html
    ):
        raise RuntimeError(
            "Got a Cloudflare/JS challenge page instead of Finviz news. "
            "You may need to use a browser automation tool (e.g. Playwright / "
            "Selenium) or an 'undetected' HTTP client."
        )

    # --- 2) Parse with BeautifulSoup ---
    soup = BeautifulSoup(html, "html.parser")

    items: List[Dict[str, Any]] = []

    # We look for all *external* article links (no finviz.com, no internal nav)
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if not href:
            continue

        # Skip finviz internal stuff
        if "finviz.com" in href or href.startswith("news.ashx") or href.startswith("/"):
            continue

        # Try to find a reasonable "row" container that also contains the time / date
        row = link.find_parent("tr")
        if row is None:
            row = link.parent

        if row is None:
            continue

        # Finviz rows typically look like:
        # "08:06AM U.S. dollar registers six-month high before retreat www.marketwatch.com"
        row_text = row.get_text(" ", strip=True)

        m = TS_RE.match(row_text)
        if not m:
            # Sometimes the direct parent might be too narrow; try grandparent as fallback
            gp = row.parent
            if gp is not None:
                row_text2 = gp.get_text(" ", strip=True)
                m = TS_RE.match(row_text2)

        if not m:
            continue

        ts = m.group("ts")
        # Title from the <a>, not from the regex, to avoid including domain
        title = link.get_text(" ", strip=True)

        full_url = urljoin(URL, href)

        items.append(
            {
                "date_or_time": ts,
                "title": title,
                "url": full_url,
            }
        )

    return items


@tool
def get_financial_market_updates(num_news: int = 20) -> Dict[str, Any]:
    """
    Use this to get news and an overview over the stock market.
    Scrape the latest Finviz headlines and split them into two buckets so the agent
    can build an overview of the current market situation.

    Args:
        num_news: Maximum number of real-time "News" headers to return. These are
            intraday headlines with a time stamp like "08:06AM". Standard is 10.

    Returns:
        A JSON-serializable dict with:
            - "news": list of dicts, each with keys "date_or_time", "title", "url"
              for live market news.
    """
    items = _scrape_finviz_news()

    return {
        "news": items[:num_news],
    }