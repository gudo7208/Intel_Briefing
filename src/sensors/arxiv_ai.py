"""
arXiv AI Sensor - 从 arXiv 获取最新 AI/ML 论文。
使用官方 arXiv API（无需认证）。
"""
import sys
import re
import logging
from dataclasses import dataclass
from typing import List
from datetime import datetime

import httpx

from src.sensors.base import BaseSensor, SensorResult, retry_request

logger = logging.getLogger(__name__)

@dataclass
class ArxivPaper:
    """An arXiv paper."""
    id: str
    title: str
    summary: str
    authors: List[str]
    published: str
    categories: List[str]
    
    @property
    def url(self) -> str:
        return f"https://arxiv.org/abs/{self.id}"
    
    @property
    def pdf_url(self) -> str:
        return f"https://arxiv.org/pdf/{self.id}.pdf"

def fetch_ai_papers(limit: int = 10) -> List[ArxivPaper]:
    """获取 arXiv 最新 AI/ML 论文（带重试）"""
    logger.info("正在获取 arXiv 前 %d 篇 AI 论文...", limit)

    query = "cat:cs.AI"
    api_url = (
        f"https://export.arxiv.org/api/query?search_query={query}"
        f"&start=0&max_results={limit}"
        f"&sortBy=submittedDate&sortOrder=descending"
    )

    try:
        resp = retry_request(lambda: httpx.get(api_url, timeout=30))
        xml = resp.text

        if len(xml) < 500:
            logger.debug("响应过短 (%d bytes)", len(xml))
            return []
    except Exception as e:
        logger.error("请求失败: %s", e)
        return []
    
    papers = []
    # Simple XML parsing (avoid heavy dependencies)
    entries = re.findall(r'<entry>(.*?)</entry>', xml, re.DOTALL)
    
    for entry in entries:
        arxiv_id_match = re.search(r'<id>http://arxiv.org/abs/([^<]+)</id>', entry)
        title_match = re.search(r'<title>([^<]+)</title>', entry)
        summary_match = re.search(r'<summary>([^<]+)</summary>', entry, re.DOTALL)
        published_match = re.search(r'<published>([^<]+)</published>', entry)
        authors = re.findall(r'<name>([^<]+)</name>', entry)
        categories = re.findall(r'<category term="([^"]+)"', entry)
        
        if arxiv_id_match and title_match:
            papers.append(ArxivPaper(
                id=arxiv_id_match.group(1),
                title=title_match.group(1).strip().replace('\n', ' '),
                summary=(summary_match.group(1).strip()[:500] + "...") if summary_match else "",
                authors=authors[:3],  # First 3 authors
                published=published_match.group(1)[:10] if published_match else "",
                categories=categories[:3]
            ))
    
    return papers

class ArxivSensor(BaseSensor):
    """arXiv AI 传感器，基于 BaseSensor 统一接口"""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "ArXiv AI"

    def fetch(self, limit: int = 10) -> List[SensorResult]:
        """获取数据并转换为统一的 SensorResult 格式"""
        papers = fetch_ai_papers(limit)
        return [
            SensorResult(
                title=p.title,
                url=p.url,
                source="ArXiv",
                category="research",
                timestamp=p.published,
                summary=", ".join(p.authors[:2]),
                metadata={"categories": ", ".join(p.categories[:2])},
            )
            for p in papers
        ]


def print_papers(papers: List[ArxivPaper]):
    """以可读格式打印论文列表"""
    print(f"\n{'='*60}")
    print(f"  arXiv AI/ML Latest Papers")
    print(f"{'='*60}\n")

    for i, p in enumerate(papers, 1):
        print(f"{i}. {p.title}")
        print(f"   {', '.join(p.authors)}")
        print(f"   {p.published} | {', '.join(p.categories)}")
        print(f"   {p.url}")
        print()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    sensor = ArxivSensor()
    results = sensor.fetch_with_cache(limit)
    if results:
        for i, r in enumerate(results, 1):
            print(f"{i}. {r.title}")
            print(f"   {r.summary}")
            print(f"   {r.timestamp} | {r.metadata.get('categories', '')}")
            print(f"   {r.url}")
            print()
    else:
        logger.warning("未获取到任何论文。")
