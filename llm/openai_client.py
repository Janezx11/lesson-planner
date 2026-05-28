"""
通用 OpenAI 兼容客户端

一个客户端类支持所有 OpenAI 兼容的 LLM 提供商（Qwen、LongCat、DeepSeek、Groq 等）。
Provider 特异性完全由 LLMConfig 驱动（base_url、api_key、model）。
"""

import json
from typing import Dict, Any, Optional
from time import sleep

from utils.logger import get_logger
from .base import BaseLLMClient
from .config import LLMConfig
from .json_repair import parse_llm_json
from utils.parser import JSONParsingError

logger = get_logger(__name__)

# Python type -> JSON Schema type string
_TYPE_MAP = {
    str: "string",
    int: "number",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


class OpenAICompatibleClient(BaseLLMClient):
    """通用 OpenAI 兼容客户端。

    支持任何实现了 OpenAI Chat Completions API 的服务：
    - OpenAI、Azure OpenAI
    - Qwen (dashscope 兼容模式)
    - LongCat、DeepSeek、Moonshot、Zhipu、Groq、Together AI
    - Ollama、vLLM 等本地部署

    所有 provider 差异通过 config.base_url / config.model 驱动。
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._init_client()

    def _init_client(self) -> None:
        """初始化 OpenAI 客户端。"""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai 包未安装。请运行: pip install openai"
            )

        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout,
        )
        logger.info(
            f"OpenAI 兼容客户端就绪: model={self.config.model} "
            f"base_url={self.config.base_url}"
        )

    # ---- Schema 工具 ----

    @staticmethod
    def _convert_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
        """递归将 Python 类型转换为 JSON Schema 类型字符串。"""
        if not isinstance(schema, dict):
            return schema
        result = {}
        for key, value in schema.items():
            if key == "type" and isinstance(value, type):
                result[key] = _TYPE_MAP.get(value, "string")
            elif isinstance(value, type):
                result[key] = _TYPE_MAP.get(value, "string")
            elif isinstance(value, dict):
                result[key] = OpenAICompatibleClient._convert_schema(value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _inline_refs(schema: Dict[str, Any]) -> Dict[str, Any]:
        """将 $ref 引用展开为内联 schema，消除 $defs。

        很多 LLM 的 json_schema 模式不支持 $ref，需要展平。
        """
        import copy
        schema = copy.deepcopy(schema)
        defs = schema.pop("$defs", {})

        def resolve_refs(obj):
            if isinstance(obj, dict):
                if "$ref" in obj:
                    ref_path = obj["$ref"]
                    name = ref_path.rsplit("/", 1)[-1]
                    if name in defs:
                        return resolve_refs(defs[name])
                    return obj
                return {k: resolve_refs(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [resolve_refs(item) for item in obj]
            return obj

        return resolve_refs(schema)

    # ---- 公开 API ----

    def generate_structured_output(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        required_fields: Optional[list] = None,
    ) -> Dict[str, Any]:
        """调用 LLM 并返回匹配 schema 的解析后 JSON。

        使用 json_object 模式 + schema 注入 prompt + 4 层 JSON 修复。
        兼容所有 OpenAI 兼容 API（包括 json_schema 支持不稳定的模型）。

        Args:
            prompt: 用户提示
            schema: JSON Schema
            system_prompt: 系统提示
            required_fields: 必须存在的字段列表，缺失时会重试
        """
        clean_schema = self._convert_schema(schema)
        schema_json = json.dumps(clean_schema, ensure_ascii=False, indent=2)

        # 构建系统提示（注入 schema + 格式强制要求）
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
                    raise OpenAICompatibleResponseError("API 返回了空内容")

                # 使用统一的 4 层容错解析
                result = parse_llm_json(raw)

                # 验证必需字段
                if required_fields:
                    missing = [f for f in required_fields if f not in result]
                    if missing:
                        logger.warning(
                            f"Attempt {attempt+1}: 缺少必需字段: {missing}. "
                            f"已有字段: {list(result.keys())}"
                        )
                        if attempt < 2:
                            field_emphasis = (
                                f"\n\n【严重警告】你的上次输出缺少必需字段: {missing}\n"
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

        raise OpenAICompatibleResponseError(
            f"3 次尝试后仍然失败: {last_err}"
        ) from last_err

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """调用 LLM 并返回纯文本。"""
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
            logger.error(f"文本生成失败: {e}")
            raise OpenAICompatibleResponseError(str(e)) from e


# ---- 异常类 ----


class OpenAICompatibleError(Exception):
    """OpenAI 兼容客户端基础错误。"""
    pass


class OpenAICompatibleResponseError(OpenAICompatibleError):
    """API 响应错误。"""
    pass