"""
Grok/xAI LLM Provider — 封装现有的 Grok API 调用逻辑。
支持官方 API 和中转站（Relay）两种模式。
"""

import os
import logging
from typing import List, Dict

import httpx
from dotenv import load_dotenv

from src.llm.base import LLMProvider

load_dotenv()
logger = logging.getLogger(__name__)


class GrokProvider(LLMProvider):
    """Grok/xAI LLM 提供者，通过 OpenAI 兼容接口调用 Grok 模型"""

    def __init__(self):
        self.api_key = os.getenv("XAI_API_KEY")
        self.base_url = os.getenv(
            "XAI_BASE_URL", "https://api.x.ai/v1/chat/completions"
        )
        self.model = os.getenv("XAI_MODEL", "grok-beta")

    @property
    def name(self) -> str:
        return "Grok"

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.5,
        timeout: int = 60,
    ) -> str:
        """调用 Grok API 进行对话。

        Args:
            messages: OpenAI 格式消息列表
            temperature: 生成温度
            timeout: 超时时间（秒）

        Returns:
            模型回复文本，出错时返回错误信息字符串
        """
        if not self.api_key:
            logger.error("XAI_API_KEY 未配置")
            return "Error: XAI_API_KEY 未配置"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
        }

        try:
            response = httpx.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            err = f"Grok API 错误: {e.response.status_code}"
            logger.error(err)
            return err
        except Exception as e:
            err = f"Grok 连接错误: {e}"
            logger.error(err)
            return err
