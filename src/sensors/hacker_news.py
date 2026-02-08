"""
Hacker News Sensor - 从 Hacker News 获取热门文章。
使用官方 Firebase API（无需认证）。
- 批量并发请求解决 N+1 问题
- 指数退避重试
- 文件缓存避免重复抓取
"""
import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional

import httpx

from sensors.base import BaseSensor, SensorResult, retry_request

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

def _fetch_story(sid: int) -> Optional[HNStory]:
    """获取单个 story 详情（带重试）"""
    try:
        resp = retry_request(
            lambda _sid=sid: httpx.get(
                f"https://hacker-news.firebaseio.com/v0/item/{_sid}.json",
                timeout=10,
            ),
        )
        item = resp.json()
        if item and item.get("type") == "story":
            return HNStory(
                id=item["id"],
                title=item.get("title", ""),
                url=item.get("url"),
                score=item.get("score", 0),
                by=item.get("by", "unknown"),
                descendants=item.get("descendants", 0),
            )
    except Exception as e:
        logger.warning("获取 story %d 失败: %s", sid, e)
    return None


def fetch_top_stories(limit: int = 10) -> List[HNStory]:
    """获取 Hacker News 热门文章（批量并发请求）"""
    logger.info("正在获取 Hacker News 前 %d 篇文章...", limit)

    # 获取热门文章 ID 列表（带重试）
    resp = retry_request(
        lambda: httpx.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=15,
        ),
    )
    story_ids = resp.json()[:limit]

    # 批量并发获取 story 详情，解决 N+1 问题
    stories: List[HNStory] = []
    with ThreadPoolExecutor(max_workers=min(limit, 10)) as pool:
        futures = {pool.submit(_fetch_story, sid): sid for sid in story_ids}
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                stories.append(result)

    # 按 score 降序排列，保持稳定顺序
    stories.sort(key=lambda s: s.score, reverse=True)
    return stories

class HackerNewsSensor(BaseSensor):
    """Hacker News 传感器，基于 BaseSensor 统一接口"""

    @property
    def name(self) -> str:
        return "Hacker News"

    def fetch(self, limit: int = 10) -> List[SensorResult]:
        """获取数据并转换为统一的 SensorResult 格式"""
        stories = fetch_top_stories(limit)
        return [
            SensorResult(
                title=s.title,
                url=s.url or s.hn_url,
                source="Hacker News",
                category="tech_trends",
                heat=f"{s.score} points",
                summary=f"{s.descendants} comments | by {s.by}",
            )
            for s in stories
        ]


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
    results = sensor.fetch_with_cache(limit)
    if results:
        for i, r in enumerate(results, 1):
            print(f"{i}. {r.title}")
            print(f"   {r.heat} | {r.summary}")
            print(f"   {r.url}")
            print()
    else:
        logger.warning("未获取到任何文章。")
