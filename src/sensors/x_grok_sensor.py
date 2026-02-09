import os
import sys
import datetime
import json
import logging
from dotenv import load_dotenv
from typing import List

from src.sensors.base import BaseSensor, SensorResult
from src.llm.factory import get_llm_provider

logger = logging.getLogger(__name__)

# Force UTF-8 stdout (may fail on some Linux systems)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, OSError):
    pass

# Load environment variables
load_dotenv()

# 保留 XAI_API_KEY 用于 is_available() 检查
XAI_API_KEY = os.getenv("XAI_API_KEY")

def fetch_grok_intel(query: str, override_prompt: str = None) -> str:
    """通过 LLM 抽象层获取情报，返回 markdown 报告。

    已重构为使用统一的 LLMProvider 接口，不再直接调用 httpx。
    """
    logger.info("Grok Sensor: 正在查询 '%s'...", query)

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    year_str = datetime.datetime.now().strftime("%Y")

    if override_prompt:
        system_content = f"You are an specialized Data Analyst. Current Date: {today_str}. Follow the user's instructions strictly."
        user_content = override_prompt
    else:
        system_content = (
            f"You are a Commercial Intelligence Analyst. **CURRENT DATE: {today_str}**. "
            "Your goal is to find high-signal discussions from the **LAST 24 HOURS ONLY**. "
            f"❌ CRITICAL RULE: Do NOT report events from {int(year_str)-2} or {int(year_str)-1} as 'new'. "
            "If the trend is from 2024/2025, explicitly label it as 'Historical Context'. "
            "**IMPORTANT: You must answer in Simplified Chinese (简体中文).**"
        )
        user_content = f"Search X for the latest trends about '{query}' happened in {year_str}. Focus on specific recent events. Reply in Chinese."

    try:
        # 通过工厂函数获取当前配置的 LLM Provider
        llm = get_llm_provider()
        content = llm.analyze(system_content, user_content, timeout=60)

        logger.info("情报报告已生成: %s", query)
        logger.debug(content)
        return content

    except Exception as e:
        err = f"LLM 调用错误: {e}"
        logger.error(err)
        return err

class GrokSensor(BaseSensor):
    """Grok/X 传感器，基于 BaseSensor 统一接口"""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "Grok/X"

    def is_available(self) -> bool:
        return XAI_API_KEY is not None

    def fetch(self, limit: int = 10) -> List[SensorResult]:
        """获取数据并转换为统一的 SensorResult 格式"""
        report = fetch_grok_intel("AI Agents, LLM, Tech Startups")
        if report and "Error" not in report:
            return [
                SensorResult(
                    title="X/Grok Intelligence Report",
                    url="https://x.com",
                    source="X (via Grok)",
                    category="social",
                    summary=report[:200],
                    metadata={"content": report, "type": "markdown_report"},
                )
            ]
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    if len(sys.argv) < 2:
        print("Usage: python x_grok_sensor.py <query>")
        print("Example: python x_grok_sensor.py 'AI Agents'")
    else:
        q = sys.argv[1]
        result = fetch_grok_intel(q)
        print(result)
