"""
LLM Provider 工厂函数 — 根据 .env 配置自动选择 LLM 后端。

优先级逻辑：
1. 如果设置了 LLM_PROVIDER 环境变量，直接使用指定的 Provider
2. 否则自动检测：优先 Grok（有 XAI_API_KEY），其次 OpenAI（有 OPENAI_API_KEY）
"""

import os
import logging

from dotenv import load_dotenv

from src.llm.base import LLMProvider

load_dotenv()
logger = logging.getLogger(__name__)

# 支持的 Provider 名称映射
_PROVIDER_MAP = {
    "grok": "src.llm.grok_provider.GrokProvider",
    "xai": "src.llm.grok_provider.GrokProvider",
    "openai": "src.llm.openai_provider.OpenAIProvider",
}


def get_llm_provider(provider_name: str = None) -> LLMProvider:
    """根据配置创建并返回 LLM Provider 实例。

    Args:
        provider_name: 指定 Provider 名称（可选）。
                       如果不传，则从 LLM_PROVIDER 环境变量读取，
                       再不行则自动检测可用的 API Key。

    Returns:
        LLMProvider 实例

    Raises:
        ValueError: 未找到可用的 LLM Provider 或名称无效
    """
    # 第一优先级：函数参数
    name = provider_name

    # 第二优先级：环境变量
    if not name:
        name = os.getenv("LLM_PROVIDER", "").strip().lower()

    # 第三优先级：自动检测可用的 API Key
    if not name:
        if os.getenv("XAI_API_KEY"):
            name = "grok"
            logger.info("自动检测到 XAI_API_KEY，使用 Grok Provider")
        elif os.getenv("OPENAI_API_KEY"):
            name = "openai"
            logger.info("自动检测到 OPENAI_API_KEY，使用 OpenAI Provider")

    if not name:
        raise ValueError(
            "未找到可用的 LLM Provider。"
            "请在 .env 中设置 LLM_PROVIDER 或配置对应的 API Key "
            "(XAI_API_KEY / OPENAI_API_KEY)"
        )

    # 查找 Provider 类路径
    class_path = _PROVIDER_MAP.get(name)
    if not class_path:
        available = ", ".join(sorted(_PROVIDER_MAP.keys()))
        raise ValueError(
            f"不支持的 LLM Provider: '{name}'。可选值: {available}"
        )

    # 动态导入并实例化
    module_path, class_name = class_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    provider_cls = getattr(module, class_name)
    instance = provider_cls()

    logger.info("已初始化 LLM Provider: %s (模型: %s)", instance.name, getattr(instance, 'model', 'N/A'))
    return instance
