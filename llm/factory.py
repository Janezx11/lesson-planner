"""
LLM Factory

Conversion layer: extracts LLMConfig from LangGraph state,
then delegates client creation to LLMClientFactory.

State (business) -> LLMConfig (model only) -> Client
"""

from typing import Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)


def get_llm_for_state(state: Dict[str, Any]):
    """
    Main entry point for LangGraph nodes.

    1. Extract provider from state
    2. Build LLMConfig (only model params, never topic/grade)
    3. Create and return the client
    """
    from .config import LLMConfig
    from .base import LLMClientFactory

    if "provider" not in state:
        raise ValueError("State must contain 'provider' field")

    provider = state["provider"]
    logger.info(f"Creating LLM client for provider: {provider}")

    config = LLMConfig.from_state(provider, state)
    return LLMClientFactory.create(provider, config)


# ---- Provider auto-registration ----
# Each provider module registers itself at import time.
# This block triggers those imports once.

def _register_providers():
    """注册特殊客户端。

    只有 Claude 需要显式注册（使用 Anthropic SDK，非 OpenAI 格式）。
    其他 provider 由 LLMClientFactory.create() 按 config.sdk 自动路由到
    OpenAICompatibleClient，无需注册。
    """
    from .base import LLMClientFactory

    try:
        from .claude import ClaudeClient
        LLMClientFactory.register("claude", ClaudeClient)
    except ImportError as e:
        logger.warning(f"Claude not available: {e}")


_register_providers()