import os
import sys
import datetime
import json
import logging
import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Force UTF-8 stdout (may fail on some Linux systems)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, OSError):
    pass

# Load environment variables
load_dotenv()

# Configuration
XAI_API_KEY = os.getenv("XAI_API_KEY")
# Default to official endpoint, but allow override for Relay Services (中转站)
XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1/chat/completions")
MODEL_NAME = os.getenv("XAI_MODEL", "grok-beta")  # Relay users: set to 'grok-3' or 'grok-4'

def fetch_grok_intel(query: str, override_prompt: str = None) -> str:
    """
    Fetch intelligence from X using xAI's Grok API.
    Returns the markdown report.
    """
    if not XAI_API_KEY:
        logger.error("XAI_API_KEY 未在 .env 中找到")
        return "Error: No API Key."

    logger.info("Grok Sensor: 正在联系 xAI 查询 '%s'...", query)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {XAI_API_KEY}"
    }

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

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {XAI_API_KEY}"
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system", 
                "content": system_content
            },
            {
                "role": "user", 
                "content": user_content
            }
        ],
        "stream": False,
        "temperature": 0.5
    }

    try:
        response = httpx.post(XAI_BASE_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        content = data['choices'][0]['message']['content']
        
        logger.info("Grok 情报报告: %s", query)
        logger.debug(content)
        
        return content
        
    except httpx.HTTPStatusError as e:
        err = f"API 错误: {e.response.status_code}"
        logger.error(err)
        return err
    except Exception as e:
        err = f"连接错误: {e}"
        logger.error(err)
        return err

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python x_grok_sensor.py <query>")
        print("Example: python x_grok_sensor.py 'AI Agents'")
    else:
        q = sys.argv[1]
        fetch_grok_intel(q)
