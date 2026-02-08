"""
WallStreetCN Sensor - Fetches latest financial news from WallStreetCN (华尔街见闻).
Uses the public API (no auth required).
"""
import sys
import json
from dataclasses import dataclass
from typing import List, Optional

try:
    import httpx
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "httpx", "-q"])
    import httpx


@dataclass
class WSCNArticle:
    """A WallStreetCN news item."""
    title: str
    url: str
    summary: str
    published: str
    category: str = "WallStreetCN"


def fetch_wallstreetcn(limit: int = 10) -> List[WSCNArticle]:
    """Fetch latest news from WallStreetCN public API."""
    print(f"  -> Fetching latest {limit} items from WallStreetCN...")

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    }

    articles = []

    # Try the live feed API (newsflash / 7x24)
    try:
        api_url = "https://api-one-wscn.awtmt.com/apiv1/content/lives"
        params = {"channel": "global-channel", "limit": limit}
        resp = httpx.get(api_url, params=params, headers=headers, timeout=15)
        data = resp.json()
        items = data.get("data", {}).get("items", [])

        for item in items[:limit]:
            title = item.get("title", "") or item.get("content_text", "")
            content = item.get("content_text", "")
            display_time = item.get("display_time", "")
            item_id = item.get("id", "")

            if not title and content:
                # Use first 80 chars of content as title
                title = content[:80]

            if not title:
                continue

            articles.append(WSCNArticle(
                title=title[:200],
                url=f"https://wallstreetcn.com/live/{item_id}" if item_id else "https://wallstreetcn.com",
                summary=content[:200] if content else "",
                published=str(display_time),
            ))

        if articles:
            return articles
    except Exception as e:
        print(f"    Live feed API failed: {e}")

    # Fallback: articles API
    try:
        art_url = "https://api-one-wscn.awtmt.com/apiv1/content/articles"
        params = {"limit": limit}
        resp = httpx.get(art_url, params=params, headers=headers, timeout=15)
        data = resp.json()
        items = data.get("data", {}).get("items", [])

        for item in items[:limit]:
            title = item.get("title", "")
            summary = item.get("content_short", "")
            uri = item.get("uri", "")
            pub = item.get("display_time", "")

            if not title:
                continue

            articles.append(WSCNArticle(
                title=title,
                url=f"https://wallstreetcn.com/articles/{uri}" if uri else "https://wallstreetcn.com",
                summary=summary[:200] if summary else "",
                published=str(pub),
            ))
    except Exception as e:
        print(f"    Articles API also failed: {e}")

    return articles


def print_articles(articles: List[WSCNArticle]):
    """Print articles in a readable format."""
    print(f"\n{'='*60}")
    print(f"  WallStreetCN Latest News")
    print(f"{'='*60}\n")

    for i, a in enumerate(articles, 1):
        print(f"{i}. {a.title}")
        if a.summary:
            print(f"   {a.summary[:100]}...")
        print(f"   {a.url}")
        print()


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    articles = fetch_wallstreetcn(limit)
    if articles:
        print_articles(articles)
    else:
        print("No articles found from WallStreetCN.")
