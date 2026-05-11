"""
models - Pydantic 强类型模型模块

架构分层：
- models/cognitive/: AI 教学认知中间层 (Teaching Cognitive IR)
- models/runtime/: 教师运行时模型 (Teacher Runtime Models)

Cognitive IR 的作用（AI 内部，不暴露给教师）：
- 认知推进路线
- 知识结构分析
- 互动设计策略
- 练习题分层设计
- 易错点模型

Runtime Model 的作用（最终给教师看）：
- 课堂环节、教学活动
- 师生互动、提问追问
- 练习题、作业、板书
- 接近真实学校教案格式
- 可导出 DOCX、可渲染 Markdown

关键原则：
- Cognitive IR ≠ Teacher Runtime Model
- Compiler (LLM) 负责将 Cognitive IR 编译为 Runtime Model
- Renderer 负责将 Runtime Model 格式化为 Markdown/DOCX
"""

# Cognitive IR Models (AI 内部)
from .cognitive import (
    # Cognitive Flow
    StudentAnalysis,
    TeachingObjectives,
    CognitiveStage,
    CognitiveFlow,
    # Knowledge Structure
    CoreConcept,
    CommonMistake,
    PrerequisiteKnowledge,
    KeyInsight,
    ConceptualHierarchy,
    KnowledgeStructure,
    # Interaction Design
    TeacherBehavior,
    StudentBehavior,
    InteractionPoint,
    QuestionStrategy,
    InteractionDesign,
    # Practice Design
    PracticeQuestion,
    PracticeDesign,
    # Misconception Model
    MisconceptionItem,
    MisconceptionModel,
)

# Teacher Runtime Models (教师可读)
from .runtime import (
    ClassroomSection,
    ClassroomInteraction,
    HomeworkTask,
    BlackboardDesign,
    TeacherRuntimePlan,
)

__all__ = [
    # Cognitive IR
    "StudentAnalysis",
    "TeachingObjectives",
    "CognitiveStage",
    "CognitiveFlow",
    "CoreConcept",
    "CommonMistake",
    "PrerequisiteKnowledge",
    "KeyInsight",
    "ConceptualHierarchy",
    "KnowledgeStructure",
    "TeacherBehavior",
    "StudentBehavior",
    "InteractionPoint",
    "QuestionStrategy",
    "InteractionDesign",
    "PracticeQuestion",
    "PracticeDesign",
    "MisconceptionItem",
    "MisconceptionModel",
    # Teacher Runtime
    "ClassroomSection",
    "ClassroomInteraction",
    "HomeworkTask",
    "BlackboardDesign",
    "TeacherRuntimePlan",
]
