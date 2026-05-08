"""
LongCat API Client

Uses OpenAI-compatible SDK. Config is accessed via self.config.field.
"""

import json
from typing import Dict, Any, Optional
from time import sleep

from utils.logger import get_logger
from .base import BaseLLMClient
from .config import LLMConfig
from utils.parser import safe_parse_json, JSONParsingError

logger = get_logger(__name__)

# Python type -> JSON Schema type string
_TYPE_MAP = {str: "string", int: "number", float: "number",
             bool: "boolean", list: "array", dict: "object"}


class LongCatClient(BaseLLMClient):
    """LongCat API client (OpenAI-compatible)."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._init_openai_client()

    def _init_openai_client(self) -> None:
        """Create the underlying OpenAI client."""
        from openai import OpenAI
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )
        logger.info(
            f"LongCat client ready: model={self.config.model} "
            f"base_url={self.config.base_url}"
        )

    # ---- Schema helpers ----

    @staticmethod
    def _convert_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively convert Python types to JSON Schema type strings."""
        if not isinstance(schema, dict):
            return schema
        result = {}
        for key, value in schema.items():
            if key == "type" and isinstance(value, type):
                result[key] = _TYPE_MAP.get(value, "string")
            elif isinstance(value, type):
                result[key] = _TYPE_MAP.get(value, "string")
            elif isinstance(value, dict):
                result[key] = LongCatClient._convert_schema(value)
            else:
                result[key] = value
        return result

    # ---- JSON repair ----

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract the first JSON object from text."""
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or start >= end:
            raise JSONParsingError(f"No JSON found in: {text[:100]}")
        return text[start : end + 1]

    @staticmethod
    def _repair_json(text: str) -> str:
        """Try common fixes for broken JSON."""
        import re

        fixed = text

        # 1. 替换单引号为双引号（但不替换字符串内的）
        # 简单处理：只替换key周围的单引号
        fixed = re.sub(r"(?<=[{\[,])\s*'([^']*)'\s*:", r' "\1":', fixed)
        fixed = re.sub(r":\s*'([^']*)'", r': "\1"', fixed)

        # 2. 移除尾随逗号（在 } 或 ] 之前的逗号）
        fixed = re.sub(r",\s*([}\]])", r"\1", fixed)

        # 3. 移除开头的逗号（在 { 或 [ 之后的逗号）
        fixed = re.sub(r"([{\[])\s*,", r"\1", fixed)

        # 4. 修复缺少逗号的情况（在两个字符串之间）
        fixed = re.sub(r'"\s*\n\s*"', '",\n"', fixed)

        # 5. 修复未转义的换行符在字符串内
        fixed = fixed.replace('\n', '\\n') if '"\\n"' not in fixed else fixed

        # 6. 平衡大括号
        open_brace = fixed.count("{")
        close_brace = fixed.count("}")
        if open_brace > close_brace:
            fixed += "}" * (open_brace - close_brace)
        elif close_brace > open_brace:
            # 移除多余的 }
            for _ in range(close_brace - open_brace):
                idx = fixed.rfind("}")
                if idx != -1:
                    fixed = fixed[:idx] + fixed[idx+1:]

        # 7. 平衡方括号
        open_bracket = fixed.count("[")
        close_bracket = fixed.count("]")
        if open_bracket > close_bracket:
            fixed += "]" * (open_bracket - close_bracket)
        elif close_bracket > open_bracket:
            for _ in range(close_bracket - open_bracket):
                idx = fixed.rfind("]")
                if idx != -1:
                    fixed = fixed[:idx] + fixed[idx+1:]

        return fixed

    # ---- Public API ----

    def generate_structured_output(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        required_fields: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Call LongCat and return parsed JSON matching the schema.

        Args:
            prompt: 用户提示
            schema: JSON Schema
            system_prompt: 系统提示
            required_fields: 必须存在的字段列表，如果缺失会重试
        """
        clean_schema = self._convert_schema(schema)

        # 构建强制格式要求
        schema_json = json.dumps(clean_schema, ensure_ascii=False, indent=2)

        system_content = ""
        if system_prompt:
            system_content += f"{system_prompt}\n\n"

        system_content += (
            "【格式强制要求 - 必须严格遵守】\n"
            "你必须严格按照以下JSON结构输出，禁止使用其他字段名！\n"
            f"必须包含的顶层字段: {', '.join(clean_schema.get('properties', {}).keys())}\n\n"
            f"完整JSON结构:\n{schema_json}\n\n"
            "【禁止事项】\n"
            "- 禁止使用上述字段名之外的任何字段\n"
            "- 禁止输出JSON之外的任何文本\n"
            "- 禁止使用markdown格式\n"
            "- 每个字段都必须有实质内容，不能是空字符串或占位符\n\n"
            "【再次强调】\n"
            f"你必须输出包含以下字段的JSON: {list(clean_schema.get('properties', {}).keys())}\n"
            "如果使用了错误的字段名，你的回答将被视为错误！"
        )

        messages = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": prompt})

        # 提取schema中的顶层必需字段
        if required_fields is None:
            required_fields = clean_schema.get("required", [])

        last_err = None
        for attempt in range(3):
            try:
                resp = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    response_format={"type": "json_object"},
                    timeout=self.config.timeout,
                )
                raw = resp.choices[0].message.content
                if not raw or not raw.strip():
                    raise LongCatResponseError("Empty response from API")

                # parse - 多层容错
                result = None

                # 尝试1: 直接解析
                try:
                    json_str = self._extract_json(raw)
                    result = json.loads(json_str)
                except (json.JSONDecodeError, JSONParsingError):
                    pass

                # 尝试2: 修复后解析
                if result is None:
                    try:
                        json_str = self._extract_json(raw)
                        repaired = self._repair_json(json_str)
                        result = json.loads(repaired)
                    except (json.JSONDecodeError, JSONParsingError):
                        pass

                # 尝试3: 使用safe_parse_json作为最后手段
                if result is None:
                    try:
                        json_str = self._extract_json(raw)
                        result = safe_parse_json(json_str)
                        if "error" in result:
                            logger.warning(f"safe_parse_json returned error: {result['error']}")
                            result = None
                    except Exception:
                        pass

                # 尝试4: 提取第一个完整的JSON对象（更宽松的匹配）
                if result is None:
                    try:
                        import re
                        # 找到最外层的 { ... }
                        match = re.search(r'\{[\s\S]*\}', raw)
                        if match:
                            json_str = match.group(0)
                            repaired = self._repair_json(json_str)
                            result = json.loads(repaired)
                    except (json.JSONDecodeError, Exception):
                        pass

                if result is None:
                    raise json.JSONDecodeError("All JSON parsing attempts failed", raw, 0)

                # 验证必需字段
                if required_fields:
                    missing_fields = [f for f in required_fields if f not in result]
                    if missing_fields:
                        logger.warning(
                            f"Attempt {attempt+1}: Missing required fields: {missing_fields}. "
                            f"Got fields: {list(result.keys())}"
                        )
                        if attempt < 2:
                            # 在下一次尝试中更强调字段要求
                            field_emphasis = (
                                f"\n\n【严重警告】你的上次输出缺少必需字段: {missing_fields}\n"
                                f"你输出了这些字段: {list(result.keys())}\n"
                                f"必须包含的字段: {required_fields}\n"
                                "请严格按照要求重新输出！"
                            )
                            messages[0]["content"] += field_emphasis
                            sleep(1 * (attempt + 1))
                            continue

                return result

            except Exception as e:
                last_err = e
                logger.warning(f"Attempt {attempt+1}/3 failed: {e}")
                if attempt < 2:
                    sleep(1 * (attempt + 1))

        # all retries exhausted – try safe_parse as last resort
        fallback = safe_parse_json(raw if "raw" in dir() else "")
        if "error" not in fallback:
            return fallback
        raise LongCatResponseError(
            f"Failed after 3 attempts: {last_err}"
        ) from last_err

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Call LongCat and return plain text."""
        messages = []
        if system_prompt and system_prompt != prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                timeout=self.config.timeout,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LongCat text generation failed: {e}")
            raise LongCatResponseError(str(e)) from e


# ---- Exceptions ----

class LongCatError(Exception):
    pass


class LongCatResponseError(LongCatError):
    pass