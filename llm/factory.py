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
    from .base import LLMClientFactory

    try:
        from .longcat import LongCatClient
        LLMClientFactory.register("longcat", LongCatClient)
    except ImportError as e:
        logger.warning(f"LongCat not available: {e}")

    try:
        from .claude import ClaudeClient
        LLMClientFactory.register("claude", ClaudeClient)
    except ImportError as e:
        logger.warning(f"Claude not available: {e}")

    try:
        from .qwen import QwenClient
        LLMClientFactory.register("qwen", QwenClient)
    except ImportError as e:
        logger.warning(f"Qwen not available: {e}")


_register_providers()