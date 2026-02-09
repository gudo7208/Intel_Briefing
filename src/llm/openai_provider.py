"""
OpenAI LLM Provider — 支持 OpenAI 官方 API 及所有兼容接口。
可用于 OpenAI、Azure OpenAI、本地部署的兼容服务等。
"""

import os
import logging
from typing import List, Dict

import httpx
from dotenv import load_dotenv

from src.llm.base import LLMProvider

load_dotenv()
logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI 及兼容 API 的 LLM 提供者"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv(
            "OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions"
        )
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")

    @property
    def name(self) -> str:
        return "OpenAI"

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.5,
        timeout: int = 60,
    ) -> str:
        """调用 OpenAI 兼容 API 进行对话。

        Args:
            messages: OpenAI 格式消息列表
            temperature: 生成温度
            timeout: 超时时间（秒）

        Returns:
            模型回复文本，出错时返回错误信息字符串
        """
        if not self.api_key:
            logger.error("OPENAI_API_KEY 未配置")
            return "Error: OPENAI_API_KEY 未配置"

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
            err = f"OpenAI API 错误: {e.response.status_code}"
            logger.error(err)
            return err
        except Exception as e:
            err = f"OpenAI 连接错误: {e}"
            logger.error(err)
            return err
