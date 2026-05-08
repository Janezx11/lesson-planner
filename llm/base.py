"""
LLM Base Layer

BaseLLMClient: abstract interface all providers must implement.
LLMClientFactory: registry + factory for creating clients.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseLLMClient(ABC):
    """Abstract LLM client. All providers inherit this."""

    def __init__(self, config: "LLMConfig"):
        self.config = config
        self.config.validate()

    @abstractmethod
    def generate_structured_output(self, prompt: str, schema: Dict[str, Any],
                                   system_prompt: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        pass


class LLMClientFactory:
    """Registry + factory. Providers register themselves here."""

    _providers: Dict[str, type] = {}

    @classmethod
    def register(cls, provider_name: str, client_class: type) -> None:
        cls._providers[provider_name.lower()] = client_class
        logger.info(f"Registered LLM provider: {provider_name}")

    @classmethod
    def create(cls, provider: str, config: "LLMConfig") -> BaseLLMClient:
        provider = provider.lower()
        if provider not in cls._providers:
            available = list(cls._providers.keys())
            raise ValueError(
                f"Unsupported provider: '{provider}'. Available: {available}"
            )
        client_class = cls._providers[provider]
        return client_class(config)