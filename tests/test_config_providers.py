"""
Tests for LLMConfig provider system and sdk field.
"""

import pytest
import os
from llm.config import LLMConfig, _PROVIDER_DEFAULTS


class TestProviderDefaults:
    def test_all_providers_have_sdk(self):
        for name, defaults in _PROVIDER_DEFAULTS.items():
            assert "sdk" in defaults, f"Provider '{name}' missing 'sdk' field"
            assert defaults["sdk"] in ("openai", "anthropic"), (
                f"Provider '{name}' has invalid sdk: {defaults['sdk']}"
            )

    def test_all_providers_have_required_keys(self):
        required = {"sdk", "model", "env_key", "default_url"}
        for name, defaults in _PROVIDER_DEFAULTS.items():
            missing = required - set(defaults.keys())
            assert not missing, f"Provider '{name}' missing keys: {missing}"

    def test_claude_sdk_is_anthropic(self):
        assert _PROVIDER_DEFAULTS["claude"]["sdk"] == "anthropic"

    def test_qwen_sdk_is_openai(self):
        assert _PROVIDER_DEFAULTS["qwen"]["sdk"] == "openai"

    def test_longcat_sdk_is_openai(self):
        assert _PROVIDER_DEFAULTS["longcat"]["sdk"] == "openai"


class TestLLMConfigSdk:
    def test_from_state_claude_sdk(self):
        state = {"provider": "claude", "api_key": "test-key"}
        config = LLMConfig.from_state("claude", state)
        assert config.sdk == "anthropic"

    def test_from_state_qwen_sdk(self):
        state = {"provider": "qwen", "api_key": "test-key"}
        config = LLMConfig.from_state("qwen", state)
        assert config.sdk == "openai"

    def test_from_state_longcat_sdk(self):
        state = {"provider": "longcat", "api_key": "test-key"}
        config = LLMConfig.from_state("longcat", state)
        assert config.sdk == "openai"

    def test_sdk_field_default(self):
        config = LLMConfig(provider="test", model="test", api_key="k", base_url="http://x")
        assert config.sdk == "openai"


class TestRegisterProvider:
    def test_register_new_provider(self):
        LLMConfig.register_provider("deepseek", {
            "sdk": "openai",
            "model": "deepseek-chat",
            "env_key": "DEEPSEEK_API_KEY",
            "env_url": "DEEPSEEK_BASE_URL",
            "default_url": "https://api.deepseek.com/v1",
        })
        assert "deepseek" in _PROVIDER_DEFAULTS
        assert _PROVIDER_DEFAULTS["deepseek"]["sdk"] == "openai"
        # cleanup
        del _PROVIDER_DEFAULTS["deepseek"]

    def test_register_missing_required_raises(self):
        with pytest.raises(ValueError, match="缺少必需字段"):
            LLMConfig.register_provider("bad", {"model": "x"})

    def test_registered_provider_works_with_from_state(self):
        LLMConfig.register_provider("test_provider", {
            "sdk": "openai",
            "model": "test-model",
            "env_key": "TEST_API_KEY",
            "default_url": "http://test.local/v1",
        })
        state = {"provider": "test_provider", "api_key": "key123"}
        config = LLMConfig.from_state("test_provider", state)
        assert config.sdk == "openai"
        assert config.model == "test-model"
        assert config.api_key == "key123"
        # cleanup
        del _PROVIDER_DEFAULTS["test_provider"]


class TestBackwardCompat:
    def test_unknown_provider_raises(self):
        state = {"provider": "nonexistent"}
        with pytest.raises(ValueError, match="Unsupported provider"):
            LLMConfig.from_state("nonexistent", state)
