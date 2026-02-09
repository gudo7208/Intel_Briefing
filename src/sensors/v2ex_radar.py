import httpx
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional, Tuple
import datetime
import re
import sys
import logging

from src.sensors.base import BaseSensor, SensorResult

logger = logging.getLogger(__name__)

@dataclass
class Lead:
    source: str
    title: str
    url: str
    summary: str
    posted_date: str
    tags: List[str]
    desperation_score: int = 0  # 0 to 100+

class V2EXRadar:
    """
    Scans V2EX for 'Soft-Target' leads: Outsourcing, Jobs, and Help requests.
    Uses RSS feeds to avoid heavy anti-scraping measures.
    """
    
    RSS_FEEDS = {
        "global": "https://www.v2ex.com/index.xml",
        "jobs": "https://www.v2ex.com/feed/tab/jobs.xml"
    }

    # Keywords that signal a "Lead" (someone paying or desperate)
    MONEY_KEYWORDS = [
        "外包", "兼职", "有偿", "预算", "报价", "招", "急", "付费"
    ]
    
    # Keywords that signal "Pain" (opportunity for service/SaaS)
    PAIN_KEYWORDS = [
        "求助", "帮忙", "不懂", "救命", "怎么做", "太难", "崩溃", "无法", "报错"
    ]
    
    # "Desperation" keywords - High Emotion = High Conversion Probability
    DESPERATION_KEYWORDS = [
        "在线等", "有偿", "急", "救命", "红包", "崩溃", "求大佬", "付费解决"
    ]
    
    # Tech Stack matching User's capabilities
    TECH_KEYWORDS = [
        "FPGA", "Verilog", "Python", "爬虫", "脚本", "Web3", "Solana", 
        "Rust", "图像", "视觉", "识别", "抠图", "Automation", "Bot"
    ]

    def fetch_leads(self, days: int = 1) -> List[Lead]:
        logger.info("正在扫描 V2EX 线索（过去 %d 天）...", days)
        all_leads = []

        with httpx.Client(timeout=15.0) as client:
          for category, url in self.RSS_FEEDS.items():
            try:
                response = client.get(url)
                response.raise_for_status()
                
                # Parse XML
                root = ET.fromstring(response.content)
                
                ns = {'atom': 'http://www.w3.org/2005/Atom'} 
                
                for item in root.findall(".//item"):
                    title = item.find("title").text or ""
                    link = item.find("link").text or ""
                    description = item.find("description").text or ""
                    pub_date_str = item.find("pubDate").text or ""
                    
                    # Parse Date
                    try:
                        pub_date = datetime.datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
                        # Filter by days
                        if (datetime.datetime.now(datetime.timezone.utc) - pub_date).days > days:
                            continue
                    except Exception:
                        pass

                    # Analyze
                    tags, score = self._analyze_content(title, description)
                    
                    if tags:
                        lead = Lead(
                            source=f"V2EX-{category}",
                            title=title,
                            url=link,
                            summary=self._clean_summary(description),
                            posted_date=pub_date_str,
                            tags=tags,
                            desperation_score=score
                        )
                        all_leads.append(lead)

            except Exception as e:
                logger.warning("获取 %s 失败: %s", category, e)
        
        # Sort by Desperation Score (High to Low)
        all_leads.sort(key=lambda x: x.desperation_score, reverse=True)
        
        logger.info("从 V2EX 找到 %d 条潜在线索", len(all_leads))
        return all_leads

    def _analyze_content(self, title: str, content: str) -> Tuple[List[str], int]:
        text = (title + content).lower()
        found_tags = []
        score = 0
        
        # Check Money
        if any(k in text for k in [k.lower() for k in self.MONEY_KEYWORDS]):
            found_tags.append("💰Money")
            score += 20
            
        # Check Pain
        if any(k in text for k in [k.lower() for k in self.PAIN_KEYWORDS]):
            found_tags.append("🚑Pain")
            score += 10
            
        # Check Desperation (The "Kill Shot" Factor)
        if any(k in text for k in [k.lower() for k in self.DESPERATION_KEYWORDS]):
            found_tags.append("🔥Urgent")
            score += 100  # Massive weight as requested by Red Team
            
        # Check Tech Matches
        tech_matches = [t for t in self.TECH_KEYWORDS if t.lower() in text]
        if tech_matches:
            found_tags.append(f"🛠️{','.join(tech_matches)}")
            score += 30
            
        # Lead Qualification: Needs (Money OR Pain OR Urgent)
        if ("💰Money" in found_tags) or ("🚑Pain" in found_tags) or ("🔥Urgent" in found_tags):
             # Boost score if it matches our tech stack
            if tech_matches:
                 score += 50
            return found_tags, score
        
        return [], 0

    def _clean_summary(self, html_content: str) -> str:
        # Simple regex to remove HTML tags
        clean = re.sub('<[^<]+?>', '', html_content)
        return clean[:200] + "..." if len(clean) > 200 else clean

class V2EXSensor(BaseSensor):
    """V2EX 传感器，基于 BaseSensor 统一接口"""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "V2EX"

    def fetch(self, limit: int = 10) -> List[SensorResult]:
        """获取数据并转换为统一的 SensorResult 格式"""
        radar = V2EXRadar()
        leads = radar.fetch_leads(days=1)
        return [
            SensorResult(
                title=lead.title,
                url=lead.url,
                source="V2EX",
                category="community",
                heat=f"Score: {lead.desperation_score}",
                timestamp=lead.posted_date,
                summary=lead.summary[:100],
                metadata={"tags": lead.tags},
            )
            for lead in leads[:limit]
        ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    sensor = V2EXSensor()
    results = sensor.fetch_with_cache()
    if results:
        for i, r in enumerate(results, 1):
            print(f"[{r.heat}] {r.title}")
            print(f"   {r.url}")
            print()
    else:
        print("No V2EX leads found.")
