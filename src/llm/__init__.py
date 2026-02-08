"""
LLM 多后端抽象层。
支持 Grok/xAI、OpenAI 及兼容 API。
"""

from src.llm.base import LLMProvider
from src.llm.factory import get_llm_provider

__all__ = ["LLMProvider", "get_llm_provider"]
