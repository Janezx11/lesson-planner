"""
design_node 输出的 Pydantic Model

替代手写 _get_design_schema() JSON Schema dict。
Pydantic Model 自动生成 JSON Schema，保证类型安全。
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TeacherBehavior(BaseModel):
    """教师行为"""
    action: str = Field(description="具体行动")
    purpose: str = Field(description="行动目的")
    duration: str = Field(default="", description="建议时长")


class StudentBehavior(BaseModel):
    """学生行为"""
    action: str = Field(description="具体行动")
    cognitive_activity: str = Field(description="认知活动")
    expected_outcome: str = Field(default="", description="预期结果")


class InteractionDesign(BaseModel):
    """互动设计（学科无关）"""
    stage_name: str = Field(description="阶段名称")
    interaction_type: str = Field(description="互动类型")
    pedagogy_method: str = Field(default="", description="教学方法")
    teacher_behavior: TeacherBehavior = Field(description="教师行为")
    student_behavior: StudentBehavior = Field(description="学生行为")
    interaction_goal: str = Field(default="", description="互动目标")
    cognitive_level: str = Field(default="", description="认知层次")
    scaffolding_strategy: str = Field(default="", description="支架策略")
    transition_to_next: str = Field(default="", description="过渡到下一阶段")


class QuestionStrategy(BaseModel):
    """提问策略"""
    approach: str = Field(default="", description="提问方式")
    progression: str = Field(default="", description="递进路径")
    techniques: List[str] = Field(default_factory=list, description="提问技巧")


class EngagementPattern(BaseModel):
    """参与模式"""
    pattern_name: str = Field(description="模式名称")
    when_to_use: str = Field(default="", description="使用时机")
    how_to_implement: str = Field(default="", description="实施方法")
    expected_effect: str = Field(default="", description="预期效果")


class FeedbackMechanism(BaseModel):
    """反馈机制"""
    type: str = Field(description="反馈类型")
    trigger: str = Field(default="", description="触发条件")
    response: str = Field(default="", description="反馈响应")
    purpose: str = Field(default="", description="反馈目的")


class DesignOutput(BaseModel):
    """design_node 的结构化输出（学科无关）"""

    interaction_design: List[InteractionDesign] = Field(
        default_factory=list,
        description="互动设计列表"
    )
    question_strategy: QuestionStrategy = Field(
        default_factory=QuestionStrategy,
        description="提问策略"
    )
    engagement_patterns: List[EngagementPattern] = Field(
        default_factory=list,
        description="参与模式列表"
    )
    feedback_mechanisms: List[FeedbackMechanism] = Field(
        default_factory=list,
        description="反馈机制列表"
    )
