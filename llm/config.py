"""
LLM Configuration

Strict data class for LLM model parameters only.
Business fields (topic, grade, etc.) must never enter this class.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import os


# Only these keys are allowed to be extracted from state
_ALLOWED_KEYS = {"provider", "model", "temperature", "max_tokens",
                 "base_url", "api_key", "timeout"}

# Provider -> (default_model, env_key_var, env_key_url)
_PROVIDER_DEFAULTS = {
    "claude": {
        "model": "claude-3-5-sonnet-20241022",
        "env_key": "ANTHROPIC_API_KEY",
        "env_url": "ANTHROPIC_BASE_URL",
        "default_url": "https://api.anthropic.com/v1",
    },
    "longcat": {
        "model": "LongCat-Flash-Lite",
        "env_key": "LONGCAT_API_KEY",
        "env_url": "LONGCAT_BASE_URL",
        "default_url": "https://api.longcat.chat/openai",
    },
    "qwen": {
        "model": "qwen-plus",
        "env_key": "QWEN_API_KEY",
        "env_url": "QWEN_BASE_URL",
        "default_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
}


@dataclass
class LLMConfig:
    """LLM model configuration. No business fields allowed."""

    provider: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    timeout: int = 30

    @classmethod
    def from_state(cls, provider: str, state: Dict[str, Any]) -> "LLMConfig":
        """
        Extract ONLY LLM config fields from a LangGraph state.

        Business fields like topic / grade are silently ignored.
        Never uses **state.
        """
        if provider not in _PROVIDER_DEFAULTS:
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Available: {list(_PROVIDER_DEFAULTS.keys())}"
            )

        defaults = _PROVIDER_DEFAULTS[provider]

        # 1. Start with provider defaults
        model = defaults["model"]
        base_url = defaults["default_url"]
        api_key = os.getenv(defaults["env_key"], "")
        temperature = 0.7
        max_tokens = 4096
        timeout = 30

        # 2. Override from llm_config sub-dict (provider-specific)
        llm_section = state.get("llm_config", {})
        if isinstance(llm_section, dict):
            provider_section = llm_section.get(provider, {})
            if isinstance(provider_section, dict):
                model = provider_section.get("model", model)
                base_url = provider_section.get("base_url", base_url)
                api_key = provider_section.get("api_key", api_key)
                temperature = provider_section.get("temperature", temperature)
                max_tokens = provider_section.get("max_tokens", max_tokens)
                timeout = provider_section.get("timeout", timeout)

        # 3. Override from top-level state (only known keys)
        model = state.get("model", model)
        base_url = state.get("base_url", base_url)
        api_key = state.get("api_key", api_key)
        temperature = state.get("temperature", temperature)
        max_tokens = state.get("max_tokens", max_tokens)
        timeout = state.get("timeout", timeout)

        # 4. Resolve env fallback for base_url
        if base_url == defaults["default_url"]:
            env_url = os.getenv(defaults["env_url"], "")
            if env_url:
                base_url = env_url

        return cls(
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )

    @classmethod
    def from_env(cls, provider: str) -> "LLMConfig":
        """Create config purely from environment variables."""
        if provider not in _PROVIDER_DEFAULTS:
            raise ValueError(f"Unsupported provider: {provider}")

        defaults = _PROVIDER_DEFAULTS[provider]
        return cls(
            provider=provider,
            model=os.getenv(f"{provider.upper()}_MODEL", defaults["model"]),
            api_key=os.getenv(defaults["env_key"], ""),
            base_url=os.getenv(defaults["env_url"], defaults["default_url"]),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
            timeout=int(os.getenv("LLM_TIMEOUT", "30")),
        )

    def validate(self) -> None:
        """Raise ValueError if config is invalid."""
        if not self.provider:
            raise ValueError("provider is required")
        if not self.model:
            raise ValueError("model is required")
        if not self.api_key:
            raise ValueError(f"api_key is required for {self.provider}")
        if not self.base_url:
            raise ValueError(f"base_url is required for {self.provider}")
        if not 0 <= self.temperature <= 2:
            raise ValueError(f"temperature must be 0-2, got {self.temperature}")
        if self.max_tokens < 1:
            raise ValueError(f"max_tokens must be positive, got {self.max_tokens}")

    def __repr__(self) -> str:
        return (
            f"LLMConfig(provider='{self.provider}', model='{self.model}', "
            f"base_url='{self.base_url}', temperature={self.temperature}, "
            f"max_tokens={self.max_tokens}, timeout={self.timeout})"
        )