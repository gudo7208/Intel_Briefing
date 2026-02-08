"""
Hacker News Sensor - 从 Hacker News 获取热门文章。
使用官方 Firebase API（无需认证）。
"""
import sys
import logging
from dataclasses import dataclass
from typing import List, Optional

import httpx

from sensors.base import BaseSensor, SensorResult

logger = logging.getLogger(__name__)

@dataclass
class HNStory:
    """A Hacker News story."""
    id: int
    title: str
    url: Optional[str]
    score: int
    by: str
    descendants: int  # comment count
    
    @property
    def hn_url(self) -> str:
        return f"https://news.ycombinator.com/item?id={self.id}"

def fetch_top_stories(limit: int = 10) -> List[HNStory]:
    """获取 Hacker News 热门文章"""
    logger.info("正在获取 Hacker News 前 %d 篇文章...", limit)

    # 获取热门文章 ID 列表
    resp = httpx.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15)
    story_ids = resp.json()[:limit]

    stories = []
    for sid in story_ids:
        item_resp = httpx.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=10)
        item = item_resp.json()
        if item and item.get("type") == "story":
            stories.append(HNStory(
                id=item["id"],
                title=item.get("title", ""),
                url=item.get("url"),
                score=item.get("score", 0),
                by=item.get("by", "unknown"),
                descendants=item.get("descendants", 0)
            ))

    return stories

class HackerNewsSensor(BaseSensor):
    """Hacker News 传感器，基于 BaseSensor 统一接口"""

    @property
    def name(self) -> str:
        return "Hacker News"

    def fetch(self, limit: int = 10) -> List[SensorResult]:
        """获取数据并转换为统一的 SensorResult 格式"""
        stories = fetch_top_stories(limit)
        results = []
        for s in stories:
            results.append(SensorResult(
                title=s.title,
                url=s.url or s.hn_url,
                source="Hacker News",
                category="tech_trends",
                heat=f"{s.score} points",
                summary=f"{s.descendants} comments | by {s.by}",
            ))
        return results


def print_stories(stories: List[HNStory]):
    """以可读格式打印文章列表"""
    print(f"\n{'='*60}")
    print(f"  Hacker News Top Stories")
    print(f"{'='*60}\n")

    for i, s in enumerate(stories, 1):
        print(f"{i}. {s.title}")
        print(f"   {s.score} points | {s.descendants} comments | by {s.by}")
        print(f"   {s.url or s.hn_url}")
        print()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    sensor = HackerNewsSensor()
    results = sensor.fetch(limit)
    if results:
        for i, r in enumerate(results, 1):
            print(f"{i}. {r.title}")
            print(f"   {r.heat} | {r.summary}")
            print(f"   {r.url}")
            print()
    else:
        logger.warning("未获取到任何文章。")
