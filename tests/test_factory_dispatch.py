"""
Tests for LLMClientFactory sdk-based dispatch.
"""

import pytest
from llm.base import LLMClientFactory
from llm.config import LLMConfig


def _make_config(provider: str, sdk: str = "openai") -> LLMConfig:
    """Create a minimal valid config for testing."""
    return LLMConfig(
        provider=provider,
        model="test-model",
        sdk=sdk,
        api_key="test-key",
        base_url="http://test.local/v1",
    )


class TestFactoryDispatch:
    def test_openai_client_for_qwen(self):
        from llm.openai_client import OpenAICompatibleClient
        config = _make_config("qwen")
        client = LLMClientFactory.create("qwen", config)
        assert isinstance(client, OpenAICompatibleClient)

    def test_openai_client_for_longcat(self):
        from llm.openai_client import OpenAICompatibleClient
        config = _make_config("longcat")
        client = LLMClientFactory.create("longcat", config)
        assert isinstance(client, OpenAICompatibleClient)

    def test_openai_client_for_custom_provider(self):
        """Unregistered provider with sdk='openai' should route to OpenAICompatibleClient."""
        from llm.openai_client import OpenAICompatibleClient
        config = _make_config("deepseek", sdk="openai")
        client = LLMClientFactory.create("deepseek", config)
        assert isinstance(client, OpenAICompatibleClient)

    def test_claude_client_registered(self):
        """Claude is registered as a special case (uses Anthropic SDK)."""
        from llm.claude import ClaudeClient
        # Claude requires the anthropic SDK, so we just check registration
        assert "claude" in LLMClientFactory._providers
        assert LLMClientFactory._providers["claude"] is ClaudeClient

    def test_unknown_sdk_raises(self):
        config = _make_config("mystery", sdk="unknown_sdk")
        with pytest.raises(ValueError, match="Unknown sdk type"):
            LLMClientFactory.create("mystery", config)
