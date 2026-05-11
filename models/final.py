"""
formatter_node 输出的 Pydantic Model

最终整合输出，包含所有节点的数据。
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from .planner import TeachingObjectives, TeachingStage
from .knowledge import KnowledgeOutput
from .design import InteractionDesign, QuestionStrategy, EngagementPattern, FeedbackMechanism
from .content import PracticeDesign, BlackboardDesign, HomeworkItem, ContentMistake, TeacherScript


class PlanMetadata(BaseModel):
    """教学方案元数据"""
    topic: str = Field(description="教学主题")
    grade: str = Field(description="年级")
    generated_at: str = Field(description="生成时间")
    version: str = Field(default="2.0", description="版本号")
    total_duration: str = Field(default="45分钟", description="总时长")


class OutputStatistics(BaseModel):
    """输出统计信息"""
    total_questions: int = Field(default=0, description="总题目数")
    basic_questions: int = Field(default=0, description="基础题数")
    intermediate_questions: int = Field(default=0, description="中等题数")
    advanced_questions: int = Field(default=0, description="拓展题数")
    interactive_points: int = Field(default=0, description="互动点数")
    homework_count: int = Field(default=0, description="作业数")
    common_mistakes_count: int = Field(default=0, description="易错点数")


class FinalOutput(BaseModel):
    """formatter_node 的最终输出"""

    metadata: PlanMetadata = Field(description="元数据")
    lesson_overview: str = Field(default="", description="课程概述")
    teaching_objectives: Optional[TeachingObjectives] = Field(default=None, description="教学目标")
    teaching_process: List[TeachingStage] = Field(default_factory=list, description="教学流程")

    # 来自 design_node
    interaction_design: List[InteractionDesign] = Field(default_factory=list, description="互动设计")
    question_strategy: Optional[QuestionStrategy] = Field(default=None, description="提问策略")
    engagement_patterns: List[EngagementPattern] = Field(default_factory=list, description="参与模式")
    feedback_mechanisms: List[FeedbackMechanism] = Field(default_factory=list, description="反馈机制")

    # 来自 content_node
    practice_design: Optional[PracticeDesign] = Field(default=None, description="练习题设计")
    blackboard_design: Optional[BlackboardDesign] = Field(default=None, description="板书设计")
    homework: List[HomeworkItem] = Field(default_factory=list, description="作业设计")
    common_mistakes: List[ContentMistake] = Field(default_factory=list, description="易错点")
    teacher_script: List[TeacherScript] = Field(default_factory=list, description="教师话术")

    # 来自 knowledge_node（可选）
    knowledge_structure: Optional[KnowledgeOutput] = Field(default=None, description="知识结构")

    # 统计信息
    statistics: Optional[OutputStatistics] = Field(default=None, description="统计信息")

    # 错误信息（可选）
    error: Optional[str] = Field(default=None, description="错误信息")
