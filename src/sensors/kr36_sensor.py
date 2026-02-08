"""
36Kr Sensor - 从36Kr获取最新科技/商业新闻。
使用公开 API（无需认证）。
"""
import sys
import json
import logging
from dataclasses import dataclass
from typing import List, Optional

import httpx

from src.sensors.base import BaseSensor, SensorResult, retry_request

logger = logging.getLogger(__name__)


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
    logger.info("正在获取 36Kr 前 %d 条新闻...", limit)

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
        logger.warning("热榜 API 失败: %s", e)

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
        logger.warning("快讯 API 也失败了: %s", e)

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


class Kr36Sensor(BaseSensor):
    """36Kr 传感器，基于 BaseSensor 统一接口"""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "36Kr"

    def fetch(self, limit: int = 10) -> List[SensorResult]:
        """获取数据并转换为统一的 SensorResult 格式"""
        articles = fetch_36kr(limit)
        return [
            SensorResult(
                title=a.title,
                url=a.url,
                source="36Kr",
                category="capital_flow",
                timestamp=a.published,
                summary=a.summary[:100] if a.summary else "",
            )
            for a in articles
        ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    sensor = Kr36Sensor()
    results = sensor.fetch_with_cache(limit)
    if results:
        for i, r in enumerate(results, 1):
            print(f"{i}. {r.title}")
            if r.summary:
                print(f"   {r.summary[:100]}...")
            print(f"   {r.url}")
            print()
    else:
        print("No articles found from 36Kr.")
