"""
graph - LangGraph 工作流模块

包含工作流构建器和状态定义。

重构说明：
- TeachingState 升级为 Pydantic BaseModel
- 支持 partial update 模式
"""

from .builder import build_teaching_copilot_graph
from .state import (
    TeachingState,
    NodeNames,
    PlannerOutput,
    KnowledgeOutput,
    DesignOutput,
    ContentOutput,
    FormatterOutput,
    NodeOutput
)

__all__ = [
    'build_teaching_copilot_graph',
    'TeachingState',
    'NodeNames',
    'PlannerOutput',
    'KnowledgeOutput',
    'DesignOutput',
    'ContentOutput',
    'FormatterOutput',
    'NodeOutput',
]
