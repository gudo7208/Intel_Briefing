"""
36Kr Sensor - Fetches latest tech/business news from 36Kr.
Uses the public newsflash API (no auth required).
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
class KrArticle:
    """A 36Kr news item."""
    title: str
    url: str
    summary: str
    published: str
    category: str = "36Kr"


def fetch_36kr(limit: int = 10) -> List[KrArticle]:
    """Fetch latest newsflash items from 36Kr public API."""
    print(f"  -> Fetching latest {limit} items from 36Kr...")

    api_url = "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Content-Type": "application/json",
    }
    payload = {"partner_id": "wap", "param": {"siteId": 1, "platformId": 2}}

    articles = []

    # Try the hot rank API first
    try:
        resp = httpx.post(api_url, json=payload, headers=headers, timeout=15)
        data = resp.json()
        items = data.get("data", {}).get("hotRankList", [])

        for item in items[:limit]:
            item_id = item.get("itemId", "")
            title = item.get("templateMaterial", {}).get("widgetTitle", "")
            summary = item.get("templateMaterial", {}).get("widgetContent", "")
            if not title:
                continue
            articles.append(KrArticle(
                title=title,
                url=f"https://36kr.com/p/{item_id}" if item_id else "https://36kr.com",
                summary=summary[:200] if summary else "",
                published="",
            ))

        if articles:
            return articles
    except Exception as e:
        print(f"    Hot rank API failed: {e}")

    # Fallback: newsflash API
    try:
        flash_url = "https://gateway.36kr.com/api/mis/nav/newsflash/flow"
        flash_payload = {
            "partner_id": "wap",
            "param": {"siteId": 1, "platformId": 2, "pageSize": limit},
        }
        resp = httpx.post(flash_url, json=flash_payload, headers=headers, timeout=15)
        data = resp.json()
        items = data.get("data", {}).get("itemList", [])

        for item in items[:limit]:
            widget = item.get("templateMaterial", {})
            title = widget.get("widgetTitle", "")
            summary = widget.get("widgetContent", "")
            pub = widget.get("publishTime", "")
            item_id = item.get("itemId", "")
            if not title:
                continue
            articles.append(KrArticle(
                title=title,
                url=f"https://36kr.com/newsflashes/{item_id}" if item_id else "https://36kr.com",
                summary=summary[:200] if summary else "",
                published=pub,
            ))
    except Exception as e:
        print(f"    Newsflash API also failed: {e}")

    return articles


def print_articles(articles: List[KrArticle]):
    """Print articles in a readable format."""
    print(f"\n{'='*60}")
    print(f"  36Kr Latest News")
    print(f"{'='*60}\n")

    for i, a in enumerate(articles, 1):
        print(f"{i}. {a.title}")
        if a.summary:
            print(f"   {a.summary[:100]}...")
        print(f"   {a.url}")
        print()


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    articles = fetch_36kr(limit)
    if articles:
        print_articles(articles)
    else:
        print("No articles found from 36Kr.")
