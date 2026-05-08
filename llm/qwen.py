"""
通义千问 (Qwen) API 封装层

提供 Qwen API 调用的统一接口，包含错误处理、重试机制和结构化输出支持。
"""

import os
import json
from typing import Dict, Any, Optional

from utils.logger import get_logger
from .base import BaseLLMClient, LLMClientFactory
from utils.parser import safe_parse_json, JSONParsingError

logger = get_logger(__name__)


class QwenClient(BaseLLMClient):
    """
    Qwen API 客户端封装

    提供 Qwen 调用的统一接口，包含错误处理、重试机制和结构化输出支持。
    """

    def __init__(self, config):
        super().__init__(config)
        self._create_client()

    def _create_client(self):
        """创建 Qwen 客户端"""
        api_key = self.config.api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        if not api_key:
            raise ValueError("Qwen API Key is required. Set it in config or DASHSCOPE_API_KEY/QWEN_API_KEY environment variable.")

        try:
            import dashscope
            dashscope.api_key = api_key
            self.client = dashscope
            logger.info(f"Created Qwen client with model: {self.config.model}")
        except ImportError:
            raise ImportError("dashscope package is required. Install it with: pip install dashscope")

    def _ensure_json_format(self, text: str) -> str:
        """
        确保文本是有效的 JSON 格式

        Args:
            text: 输入的文本

        Returns:
            格式化后的 JSON 字符串
        """
        # 查找第一个 { 到最后一个 }
        start_idx = text.find('{')
        end_idx = text.rfind('}')

        if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
            raise JSONParsingError(f"无法在文本中找到有效的 JSON 结构: {text[:100]}...")

        try:
            # 尝试直接解析
            parsed = json.loads(text[start_idx:end_idx+1])
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError as e:
            logger.warning(f"初始 JSON 解析失败，尝试修复: {e}")
            return self._repair_json(text[start_idx:end_idx+1], e)

    def _repair_json(self, text: str, original_error: Exception) -> str:
        """
        尝试修复无效的 JSON 文本

        Args:
            text: 需要修复的文本
            original_error: 原始错误信息

        Returns:
            修复后的 JSON 字符串
        """
        # 尝试常见的修复策略
        repairs = [
            # 添加缺失的引号
            (r'(\w+)\s*:', r'"\1":'),  # key: value -> "key": value
            # 修复单引号
            ("'", '"'),
            # 修复尾随逗号
            (r',\s*}', '}'),
            (r',\s*]', ']'),
        ]

        repaired_text = text
        for pattern, replacement in repairs:
            repaired_text = repaired_text.replace(pattern, replacement)

        try:
            parsed = json.loads(repaired_text)
            logger.info("成功通过修复获得有效 JSON")
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            # 如果修复失败，返回一个基本的 JSON 结构
            logger.error(f"无法修复 JSON: {original_error}")
            fallback = {"error": "JSON parsing failed", "raw_response": text}
            return json.dumps(fallback, ensure_ascii=False, indent=2)

    def generate_structured_output(self, prompt: str, schema: Dict[str, Any],
                                 system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        生成结构化输出

        Args:
            prompt: 用户提示
            schema: JSON Schema（用于指导输出结构）
            system_prompt: 系统提示（可选）

        Returns:
            解析后的字典对象

        Raises:
            QwenResponseError: API 调用失败
            JSONParsingError: JSON 解析失败且无法修复
        """
        messages = [{"role": "user", "content": prompt}]

        system_content = (
            f"{system_prompt}\n\n"
            f"请严格按照以下 JSON 格式输出，确保所有字段都存在且格式正确：\n"
            f"{json.dumps(schema, ensure_ascii=False, indent=2)}"
        ) if system_prompt else prompt

        try:
            from dashscope import Generation

            response = Generation.call(
                model=self.config.model,
                prompt=prompt,
                system=system_content if system_content != prompt else "",
                result_format="message",
                api_key=self.client.api_key,
                **{k: v for k, v in {
                    "max_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature
                }.items() if v is not None}
            )

            if response.status_code == 200:
                content_text = response.output.text

                if not content_text.strip():
                    raise QwenResponseError("API 返回了空内容")

                # 尝试解析 JSON
                try:
                    json_str = self._ensure_json_format(content_text)
                    parsed_data = json.loads(json_str)
                    logger.debug("成功解析 Qwen 结构化输出")
                    return parsed_data

                except (json.JSONDecodeError, JSONParsingError) as e:
                    logger.error("JSON 解析失败:")
                    import traceback
                    traceback.print_exc()
                    # 使用安全解析作为最后的 fallback
                    fallback_data = safe_parse_json(content_text)
                    if "error" in fallback_data:
                        raise JSONParsingError(f"无法解析 Qwen 响应为 JSON: {str(e)}") from e
                    return fallback_data

            else:
                error_msg = f"Qwen API 调用失败: {response.code} - {response.message}"
                logger.error("Qwen API 调用失败:")
                import traceback
                traceback.print_exc()
                raise QwenResponseError(error_msg)

        except Exception as e:
            logger.error("Qwen API 错误:")
            import traceback
            traceback.print_exc()
            if "dashscope" in str(type(e)):
                raise QwenResponseError(f"Qwen API 调用失败: {str(e)}") from e
            else:
                raise QwenResponseError(f"意外的错误: {str(e)}") from e

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        生成普通文本输出

        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）

        Returns:
            生成的文本

        Raises:
            QwenResponseError: API 调用失败
        """
        try:
            from dashscope import Generation

            response = Generation.call(
                model=self.config.model,
                prompt=prompt,
                system=system_prompt or "",
                result_format="message",
                api_key=self.client.api_key,
                **{k: v for k, v in {
                    "max_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature
                }.items() if v is not None}
            )

            if response.status_code == 200:
                return response.output.text.strip()
            else:
                error_msg = f"Qwen API 调用失败: {response.code} - {response.message}"
                logger.error(error_msg)
                raise QwenResponseError(error_msg)

        except Exception as e:
            logger.error(f"Qwen API 错误: {e}")
            if "dashscope" in str(type(e)):
                raise QwenResponseError(f"Qwen API 调用失败: {str(e)}") from e
            else:
                raise QwenResponseError(f"意外的错误: {str(e)}") from e


# 注册 Qwen 提供商
LLMClientFactory.register("qwen", QwenClient)


class QwenError(Exception):
    """Qwen API 错误"""
    pass


class QwenResponseError(QwenError):
    """Qwen 响应错误"""
    pass