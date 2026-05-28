"""
Claude API 封装层

提供 Claude 调用的统一接口，包含错误处理、重试机制和结构化输出支持。
"""

import os
import json
import logging
from typing import Dict, Any, Optional

from .base import BaseLLMClient, LLMClientFactory
from .json_repair import parse_llm_json
from utils.parser import JSONParsingError

logger = logging.getLogger(__name__)


class ClaudeClient(BaseLLMClient):
    """
    Claude API 客户端封装

    提供 Claude 调用的统一接口，包含错误处理、重试机制和结构化输出支持。
    """

    def __init__(self, config):
        super().__init__(config)
        self._create_client()

    def _create_client(self):
        """创建 Anthropic 客户端"""
        api_key = self.config.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Claude API Key is required. Set it in config or ANTHROPIC_API_KEY environment variable.")

        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key, timeout=self.config.timeout)
            logger.info(f"Created Claude client with model: {self.config.model}")
        except ImportError:
            raise ImportError("anthropic package is required. Install it with: pip install anthropic")

    def generate_structured_output(self, prompt: str, schema: Dict[str, Any],
                                 system_prompt: Optional[str] = None,
                                 required_fields: Optional[list] = None) -> Dict[str, Any]:
        """生成结构化输出。"""
        messages = [{"role": "user", "content": prompt}]

        system_content = (
            f"{system_prompt}\n\n"
            f"请严格按照以下 JSON 格式输出，确保所有字段都存在且格式正确：\n"
            f"{json.dumps(schema, ensure_ascii=False, indent=2)}"
        ) if system_prompt else prompt

        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_content,
                messages=messages
            )

            content_text = ""
            for block in response.content:
                if hasattr(block, 'text') and block.text:
                    content_text += block.text

            if not content_text.strip():
                raise ClaudeResponseError("API 返回了空内容")

            return parse_llm_json(content_text)

        except JSONParsingError:
            raise
        except Exception as e:
            if "anthropic" in str(type(e)):
                raise ClaudeResponseError(f"Claude API 调用失败: {str(e)}") from e
            raise ClaudeResponseError(f"意外的错误: {str(e)}") from e

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """生成纯文本输出。"""
        messages = [{"role": "user", "content": prompt}]
        system_content = system_prompt if system_prompt else None

        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_content,
                messages=messages
            )

            content_text = ""
            for block in response.content:
                if hasattr(block, 'text') and block.text:
                    content_text += block.text

            return content_text.strip()

        except Exception as e:
            if "anthropic" in str(type(e)):
                raise ClaudeResponseError(f"Claude API 调用失败: {str(e)}") from e
            raise ClaudeResponseError(f"意外的错误: {str(e)}") from e


# 注册 Claude 提供商
LLMClientFactory.register("claude", ClaudeClient)


class ClaudeError(Exception):
    """Claude API 错误"""
    pass


class ClaudeResponseError(ClaudeError):
    """Claude 响应错误"""
    pass