"""
Teaching State 定义和类型系统

这个模块定义了 AI Teaching Copilot 的 State 结构，
用于在 LangGraph 节点之间传递数据。

重构说明：
- 从 TypedDict 升级为 Pydantic BaseModel
- 节点输出字段使用 Dict[str, Any] 以支持 partial update
- 但节点内部使用强类型 Pydantic Model 处理数据
- 最终输出使用 FinalOutput 强类型 Model

LangGraph Best Practice:
- State 字段使用 Dict[str, Any] 以支持 partial update
- 节点内部使用 Pydantic Model 进行类型安全处理
- 最终输出使用强类型 Model 进行序列化
"""

from typing import Dict, Any
from pydantic import BaseModel, Field


class TeachingState(BaseModel):
    """
    AI Teaching Copilot 的核心状态定义

    LangGraph Best Practice:
    - 使用 Pydantic BaseModel 而非 TypedDict
    - 支持 model_dump()、model_copy() 等方法
    - 支持类型验证和自动序列化

    节点输出字段使用 Dict[str, Any]：
    - 这是 LangGraph partial update 的要求
    - 节点返回 {"field": value} 格式
    - LangGraph 自动合并到 state 中

    但节点内部使用强类型 Pydantic Model：
    - planner_node 使用 PlannerOutput
    - knowledge_node 使用 KnowledgeOutput
    - design_node 使用 DesignOutput
    - content_node 使用 ContentOutput
    - formatter_node 使用 FinalOutput
    """

    # 输入字段（必填）
    topic: str = Field(description="教学主题")
    grade: str = Field(description="年级信息")

    # 配置字段
    provider: str = Field(default="claude", description="LLM 提供商 (claude, qwen, longcat)")

    # 节点输出字段（由各节点填充）
    # 使用 Dict[str, Any] 以支持 LangGraph partial update
    plan: Dict[str, Any] = Field(default_factory=dict, description="教学计划 (由 planner_node 生成)")
    knowledge: Dict[str, Any] = Field(default_factory=dict, description="知识结构 (由 knowledge_node 生成)")
    design: Dict[str, Any] = Field(default_factory=dict, description="教学设计 (由 design_node 生成)")
    content: Dict[str, Any] = Field(default_factory=dict, description="教学内容 (由 content_node 生成)")
    final_output: Dict[str, Any] = Field(default_factory=dict, description="最终输出 (由 formatter_node 生成)")

    # 控制字段
    error_count: int = Field(default=0, description="错误计数，用于重试机制")
    max_retries: int = Field(default=3, description="最大重试次数")

    class Config:
        """Pydantic 配置"""
        arbitrary_types_allowed = True
        use_enum_values = True


# 默认状态初始化函数
def create_initial_state(topic: str, grade: str, provider: str = "claude") -> TeachingState:
    """创建初始状态"""
    return TeachingState(
        topic=topic,
        grade=grade,
        provider=provider,
        plan={},
        knowledge={},
        design={},
        content={},
        final_output={},
        error_count=0,
        max_retries=3
    )


# 节点间数据流转的常量定义
class NodeNames:
    PLANNER = "planner_node"
    KNOWLEDGE = "knowledge_node"
    DESIGN = "design_node"
    CONTENT = "content_node"
    FORMATTER = "formatter_node"


# 工作流边定义
class WorkflowEdges:
    PLANNER_TO_KNOWLEDGE = f"{NodeNames.PLANNER} -> {NodeNames.KNOWLEDGE}"
    KNOWLEDGE_TO_DESIGN = f"{NodeNames.KNOWLEDGE} -> {NodeNames.DESIGN}"
    DESIGN_TO_CONTENT = f"{NodeNames.DESIGN} -> {NodeNames.CONTENT}"
    CONTENT_TO_FORMATTER = f"{NodeNames.CONTENT} -> {NodeNames.FORMATTER}"
    FORMATTER_END = f"{NodeNames.FORMATTER} -> END"
