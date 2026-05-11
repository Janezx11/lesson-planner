"""
models - Pydantic 强类型模型模块

所有节点输出的 Pydantic Model 定义，
用于替代手写 JSON Schema dict。
"""

from .planner import (
    StudentAnalysis,
    TeachingObjectives,
    TeachingStage,
    PlannerOutput,
)
from .knowledge import (
    CoreConcept,
    CommonMistake,
    PrerequisiteKnowledge,
    KeyInsight,
    ConceptualHierarchy,
    KnowledgeOutput,
)
from .design import (
    TeacherBehavior,
    StudentBehavior,
    InteractionDesign,
    QuestionStrategy,
    EngagementPattern,
    FeedbackMechanism,
    DesignOutput,
)
from .content import (
    PracticeQuestion,
    PracticeDesign,
    BlackboardDesign,
    HomeworkItem,
    ContentMistake,
    TeacherScript,
    ContentExample,
    ContentOutput,
)
from .final import (
    PlanMetadata,
    FinalOutput,
)

__all__ = [
    # Planner
    "StudentAnalysis",
    "TeachingObjectives",
    "TeachingStage",
    "PlannerOutput",
    # Knowledge
    "CoreConcept",
    "CommonMistake",
    "PrerequisiteKnowledge",
    "KeyInsight",
    "ConceptualHierarchy",
    "KnowledgeOutput",
    # Design
    "TeacherBehavior",
    "StudentBehavior",
    "InteractionDesign",
    "QuestionStrategy",
    "EngagementPattern",
    "FeedbackMechanism",
    "DesignOutput",
    # Content
    "PracticeQuestion",
    "PracticeDesign",
    "BlackboardDesign",
    "HomeworkItem",
    "ContentMistake",
    "TeacherScript",
    "ContentExample",
    "ContentOutput",
    # Final
    "PlanMetadata",
    "FinalOutput",
]
