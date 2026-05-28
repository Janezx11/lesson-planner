"""
LLM Base Layer

BaseLLMClient: abstract interface all providers must implement.
LLMClientFactory: registry + factory for creating clients.

重构说明：
- 新增 generate_structured_output_v2 方法，接受 Pydantic Model 类
- 自动从 Pydantic Model 生成 JSON Schema
- 返回 Pydantic Model 实例而非 Dict
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, TypeVar
from pydantic import BaseModel
from utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseLLMClient(ABC):
    """Abstract LLM client. All providers inherit this."""

    def __init__(self, config: "LLMConfig"):
        self.config = config
        self.config.validate()

    @abstractmethod
    def generate_structured_output(self, prompt: str, schema: Dict[str, Any],
                                   system_prompt: Optional[str] = None,
                                   required_fields: Optional[list] = None) -> Dict[str, Any]:
        """生成结构化输出（旧接口，返回 Dict）"""
        pass

    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """生成纯文本输出"""
        pass

    def generate_structured_output_v2(
        self,
        prompt: str,
        output_model: Type[T],
        system_prompt: Optional[str] = None
    ) -> T:
        """
        生成结构化输出（新接口，返回 Pydantic Model）

        这是 LangGraph best practice：
        - 使用 Pydantic Model 的 model_json_schema() 自动生成 schema
        - 自动解析和验证输出
        - 返回强类型实例

        Args:
            prompt: 用户提示
            output_model: Pydantic Model 类（如 CognitiveFlow）
            system_prompt: 系统提示

        Returns:
            Pydantic Model 实例
        """
        # 从 Pydantic Model 自动生成 JSON Schema
        schema = output_model.model_json_schema()

        # 调用旧接口获取原始数据
        raw_data = self.generate_structured_output(
            prompt=prompt,
            schema=schema,
            system_prompt=system_prompt
        )

        # 使用 Pydantic 解析和验证
        # ValidationError 会自动抛出，调用方可以捕获
        return output_model.model_validate(raw_data)


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

        # 1. 优先查注册表（特殊客户端如 Claude）
        if provider in cls._providers:
            return cls._providers[provider](config)

        # 2. 按 sdk 类型自动路由
        if config.sdk == "anthropic":
            from .claude import ClaudeClient
            return ClaudeClient(config)
        elif config.sdk == "openai":
            from .openai_client import OpenAICompatibleClient
            return OpenAICompatibleClient(config)
        else:
            raise ValueError(
                f"Unknown sdk type: '{config.sdk}'. "
                f"Registered providers: {list(cls._providers.keys())}"
            )
