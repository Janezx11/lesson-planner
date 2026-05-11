"""
models/cognitive - AI 教学认知中间层 (Teaching Cognitive IR)

这是 AI 内部的教学认知结构，不是教师直接阅读的文档。

Cognitive IR 的作用：
- AI 对教学的深层理解
- 认知推进路线
- 知识结构分析
- 互动设计策略
- 练习题分层设计
- 易错点模型

这些结构会被 Rendering Layer 转换为教师可读的教案。
"""

from .cognitive_flow import (
    StudentAnalysis,
    TeachingObjectives,
    CognitiveStage,
    CognitiveFlow,
)
from .knowledge_structure import (
    CoreConcept,
    CommonMistake,
    PrerequisiteKnowledge,
    KeyInsight,
    ConceptualHierarchy,
    KnowledgeStructure,
)
from .interaction_design import (
    TeacherBehavior,
    StudentBehavior,
    InteractionPoint,
    QuestionStrategy,
    InteractionDesign,
)
from .practice_design import (
    PracticeQuestion,
    PracticeDesign,
)
from .misconception_model import (
    MisconceptionItem,
    MisconceptionModel,
)

__all__ = [
    # Cognitive Flow
    "StudentAnalysis",
    "TeachingObjectives",
    "CognitiveStage",
    "CognitiveFlow",
    # Knowledge Structure
    "CoreConcept",
    "CommonMistake",
    "PrerequisiteKnowledge",
    "KeyInsight",
    "ConceptualHierarchy",
    "KnowledgeStructure",
    # Interaction Design
    "TeacherBehavior",
    "StudentBehavior",
    "InteractionPoint",
    "QuestionStrategy",
    "InteractionDesign",
    # Practice Design
    "PracticeQuestion",
    "PracticeDesign",
    # Misconception Model
    "MisconceptionItem",
    "MisconceptionModel",
]
