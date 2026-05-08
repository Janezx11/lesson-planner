"""
Teaching State 定义和类型系统

这个模块定义了 AI Teaching Copilot 的 State 结构，
用于在 LangGraph 节点之间传递数据。
"""

from typing import TypedDict, List, Dict, Any, Optional


# Pydantic models are not used in this implementation
# All data is handled as plain dictionaries


class TeachingState(TypedDict):
    """
    AI Teaching Copilot 的核心状态定义

    每个节点负责更新特定的字段：
    - planner_node: plan
    - knowledge_node: knowledge
    - design_node: design
    - content_node: content
    - formatter_node: final_output
    """
    topic: str                    # 输入的教学主题
    grade: str                   # 年级信息
    provider: str                # LLM 提供商 (claude, qwen, longcat)
    plan: dict                   # 教学计划 (由 planner_node 生成)
    knowledge: dict             # 知识结构 (由 knowledge_node 生成)
    design: dict                # 教学设计 (由 design_node 生成)
    content: dict               # 教学内容 (由 content_node 生成)
    final_output: dict          # 最终输出 (由 formatter_node 生成)
    error_count: int            # 错误计数，用于重试机制
    max_retries: int            # 最大重试次数


# 默认状态初始化函数
def create_initial_state(topic: str, grade: str, provider: str = "claude") -> TeachingState:
    """创建初始状态"""
    return TeachingState(
        topic=topic,
        grade=grade,
        provider=provider,  # 确保 provider 字段被正确设置
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