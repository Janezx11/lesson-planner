"""
knowledge_node 输出的 Pydantic Model

替代内联手写 JSON Schema dict。
Pydantic Model 自动生成 JSON Schema，保证类型安全。
"""

from typing import List
from pydantic import BaseModel, Field


class CoreConcept(BaseModel):
    """核心概念"""
    concept: str = Field(description="概念名称")
    definition: str = Field(description="概念定义")
    importance: str = Field(description="重要程度")


class CommonMistake(BaseModel):
    """常见错误"""
    mistake: str = Field(description="错误描述")
    cause: str = Field(description="错误原因")
    solution: str = Field(description="解决方案")


class PrerequisiteKnowledge(BaseModel):
    """前置知识"""
    knowledge: str = Field(description="知识名称")
    description: str = Field(description="知识描述")
    connection: str = Field(description="与主题的关联")


class KeyInsight(BaseModel):
    """关键洞察"""
    insight: str = Field(description="洞察内容")
    explanation: str = Field(description="详细解释")
    teaching_strategy: str = Field(description="教学策略建议")


class ConceptualHierarchy(BaseModel):
    """概念层次结构"""
    basic: List[str] = Field(default_factory=list, description="基础概念")
    intermediate: List[str] = Field(default_factory=list, description="中级概念")
    advanced: List[str] = Field(default_factory=list, description="高级概念")


class KnowledgeOutput(BaseModel):
    """knowledge_node 的结构化输出"""

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
