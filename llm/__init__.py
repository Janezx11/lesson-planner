"""
llm - LLM 可插拔抽象层

支持所有 OpenAI 兼容提供商 + Anthropic Claude。
添加新 provider 只需在 LLMConfig._PROVIDER_DEFAULTS 中加一行配置。
"""

from .base import BaseLLMClient, LLMClientFactory
from .config import LLMConfig
from .factory import get_llm_for_state
from .openai_client import OpenAICompatibleClient

__all__ = [
    'BaseLLMClient',
    'LLMClientFactory',
    'LLMConfig',
    'OpenAICompatibleClient',
    'get_llm_for_state',
]
