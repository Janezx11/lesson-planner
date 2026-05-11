"""
Teaching State 定义和类型系统

这个模块定义了 AI Teaching Copilot 的 State 结构，
用于在 LangGraph 节点之间传递数据。

重构说明：
- 从 TypedDict 升级为 Pydantic BaseModel
- 增加字段类型约束和默认值
- 支持 LangGraph 的 partial update 模式
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TeachingState(BaseModel):
    """
    AI Teaching Copilot 的核心状态定义

    每个节点负责更新特定的字段：
    - planner_node: plan
    - knowledge_node: knowledge
    - design_node: design
    - content_node: content
    - formatter_node: final_output

    重构后：
    - 使用 Pydantic BaseModel 提供类型验证
    - 所有字段都有默认值
    - 支持 partial update 模式
    """
    # 输入字段（必填）
    topic: str = Field(description="教学主题")
    grade: str = Field(description="年级信息")

    # 配置字段
    provider: str = Field(default="claude", description="LLM 提供商 (claude, qwen, longcat)")

    # 节点输出字段（由各节点填充）
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
        # 允许任意类型（支持 dict 嵌套）
        arbitrary_types_allowed = True
        # 使用 enum 值
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


# 节点输出类型定义（用于类型提示）
class PlannerOutput(BaseModel):
    """planner_node 的输出"""
    plan: Dict[str, Any] = Field(description="教学计划")


class KnowledgeOutput(BaseModel):
    """knowledge_node 的输出"""
    knowledge: Dict[str, Any] = Field(description="知识结构")


class DesignOutput(BaseModel):
    """design_node 的输出"""
    design: Dict[str, Any] = Field(description="教学设计")


class ContentOutput(BaseModel):
    """content_node 的输出"""
    content: Dict[str, Any] = Field(description="教学内容")


class FormatterOutput(BaseModel):
    """formatter_node 的输出"""
    final_output: Dict[str, Any] = Field(description="最终输出")


# 所有节点输出类型的联合（用于类型提示）
NodeOutput = Dict[str, Any]  # partial update dict
