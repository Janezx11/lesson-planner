"""
graph - LangGraph 工作流模块

包含工作流构建器和状态定义。

重构说明：
- TeachingState 使用 Pydantic BaseModel
- 支持 partial update 模式
- 节点内部使用强类型 Pydantic Model
"""

from .builder import build_teaching_copilot_graph
from .state import TeachingState, NodeNames, create_initial_state

__all__ = [
    'build_teaching_copilot_graph',
    'TeachingState',
    'NodeNames',
    'create_initial_state',
]
