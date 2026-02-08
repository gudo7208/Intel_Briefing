"""
LLMProvider 抽象基类，定义所有 LLM 后端的统一接口。
所有 Provider 必须实现 chat() 和 analyze() 方法。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """LLM 提供者抽象基类，定义统一的调用接口"""

    @property
    @abstractmethod
    def name(self) -> str:
        """返回 Provider 名称，如 'Grok', 'OpenAI'"""
        ...

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.5,
        timeout: int = 60,
    ) -> str:
        """通用聊天接口，发送消息列表并返回回复文本。

        Args:
            messages: OpenAI 格式的消息列表，如 [{"role": "system", "content": "..."}]
            temperature: 生成温度，默认 0.5
            timeout: 请求超时时间（秒），默认 60

        Returns:
            LLM 回复的文本内容
        """
        ...

    def analyze(
        self,
        system_prompt: str,
        user_input: str,
        temperature: float = 0.5,
        timeout: int = 60,
    ) -> str:
        """便捷分析接口：传入 system prompt 和用户输入，返回分析结果。

        这是对 chat() 的封装，简化常见的"系统提示 + 用户输入"调用模式。

        Args:
            system_prompt: 系统提示词
            user_input: 用户输入内容
            temperature: 生成温度
            timeout: 请求超时时间（秒）

        Returns:
            LLM 回复的文本内容
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]
        return self.chat(messages, temperature=temperature, timeout=timeout)

    def __repr__(self) -> str:
        return f"<LLMProvider: {self.name}>"
