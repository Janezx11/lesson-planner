"""
Knowledge Structure - 知识结构分析

AI 对教学主题的知识结构分析。
这是 Cognitive IR 的组件之一。

LangGraph Best Practice:
- 这是 AI 内部结构，不是教师直接阅读的文档
- Renderer 会将其转换为教师可读的知识点总结
"""

from typing import List
from pydantic import BaseModel, Field


class CoreConcept(BaseModel):
    """核心概念"""
    concept: str = Field(description="概念名称")
    definition: str = Field(description="概念定义")
    importance: str = Field(default="", description="重要程度")


class CommonMistake(BaseModel):
    """常见错误"""
    mistake: str = Field(description="错误描述")
    cause: str = Field(description="错误原因")
    solution: str = Field(description="解决方案")


class PrerequisiteKnowledge(BaseModel):
    """前置知识"""
    knowledge: str = Field(description="知识名称")
    description: str = Field(default="", description="知识描述")
    connection: str = Field(default="", description="与主题的关联")


class KeyInsight(BaseModel):
    """关键洞察"""
    insight: str = Field(description="洞察内容")
    explanation: str = Field(default="", description="详细解释")
    teaching_strategy: str = Field(default="", description="教学策略建议")


class ConceptualHierarchy(BaseModel):
    """概念层次结构"""
    basic: List[str] = Field(default_factory=list, description="基础概念")
    intermediate: List[str] = Field(default_factory=list, description="中级概念")
    advanced: List[str] = Field(default_factory=list, description="高级概念")


class KnowledgeStructure(BaseModel):
    """
    知识结构（AI 内部）

    这是 knowledge_node 的核心输出，
    代表 AI 对教学主题知识结构的完整分析。

    Renderer 会将其转换为教师可读的知识点总结。
    """
    core_concepts: List[CoreConcept] = Field(default_factory=list, description="核心概念列表")
    common_mistakes: List[CommonMistake] = Field(default_factory=list, description="常见错误列表")
    prerequisite_knowledge: List[PrerequisiteKnowledge] = Field(default_factory=list, description="前置知识列表")
    key_insights: List[KeyInsight] = Field(default_factory=list, description="关键洞察列表")
    conceptual_hierarchy: ConceptualHierarchy = Field(
        default_factory=ConceptualHierarchy,
        description="概念层次结构"
    )
    learning_difficulties: List[str] = Field(default_factory=list, description="学习难点")
    critical_thinking_points: List[str] = Field(default_factory=list, description="思辨要点")
