"""
Interaction Design - 互动设计

AI 对课堂互动的设计策略。
这是 Cognitive IR 的组件之一。

LangGraph Best Practice:
- 这是 AI 内部结构（学科无关）
- Renderer 会将其转换为教师可读的互动环节说明
"""

from typing import List
from pydantic import BaseModel, Field


class TeacherBehavior(BaseModel):
    """教师行为"""
    action: str = Field(description="具体行动")
    purpose: str = Field(default="", description="行动目的")
    duration: str = Field(default="", description="建议时长")


class StudentBehavior(BaseModel):
    """学生行为"""
    action: str = Field(description="具体行动")
    cognitive_activity: str = Field(default="", description="认知活动")
    expected_outcome: str = Field(default="", description="预期结果")


class InteractionPoint(BaseModel):
    """
    互动点（AI 内部）

    这是 AI 对某个互动环节的设计，
    包含教师行为、学生行为、互动目标等。

    Renderer 会将其转换为教师可读的互动说明。
    """
    stage_name: str = Field(description="阶段名称")
    interaction_type: str = Field(default="", description="互动类型")
    pedagogy_method: str = Field(default="", description="教学方法")
    teacher_behavior: TeacherBehavior = Field(default_factory=TeacherBehavior, description="教师行为")
    student_behavior: StudentBehavior = Field(default_factory=StudentBehavior, description="学生行为")
    interaction_goal: str = Field(default="", description="互动目标")
    cognitive_level: str = Field(default="", description="认知层次")
    scaffolding_strategy: str = Field(default="", description="支架策略")


class QuestionStrategy(BaseModel):
    """提问策略"""
    approach: str = Field(default="", description="提问方式")
    progression: str = Field(default="", description="递进路径")
    techniques: List[str] = Field(default_factory=list, description="提问技巧")


class InteractionDesign(BaseModel):
    """
    互动设计（AI 内部，学科无关）

    这是 design_node 的核心输出，
    代表 AI 对课堂互动的完整设计。

    Renderer 会将其转换为教师可读的互动环节说明。
    """
    interaction_points: List[InteractionPoint] = Field(
        default_factory=list,
        description="互动点列表"
    )
    question_strategy: QuestionStrategy = Field(
        default_factory=QuestionStrategy,
        description="提问策略"
    )
