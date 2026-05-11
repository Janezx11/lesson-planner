"""
TeacherRuntimePlan - 教师运行时教案模型

最终给教师看的教案结构，不包含任何认知科学术语。
接近真实学校教案格式，可直接用于课堂教学。
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from .classroom_section import ClassroomSection
from .classroom_interaction import ClassroomInteraction
from .practice_question import PracticeQuestion
from .homework_task import HomeworkTask
from .blackboard_design import BlackboardDesign


class TeacherRuntimePlan(BaseModel):
    """教师运行时教案 — 最终给教师看的教案结构"""

    # 基本信息
    topic: str = Field(description="教学主题")
    grade: str = Field(description="年级")
    duration: str = Field(default="45分钟", description="课时时长")
    teaching_methods: List[str] = Field(default_factory=list, description="教学方法")

    # 教学目标（教师语言，非认知术语）
    teaching_objectives: List[str] = Field(default_factory=list, description="教学目标")
    key_points: List[str] = Field(default_factory=list, description="教学重点")
    difficult_points: List[str] = Field(default_factory=list, description="教学难点")

    # 教学环节（核心）
    sections: List[ClassroomSection] = Field(default_factory=list, description="教学环节")

    # 课堂互动
    interactions: List[ClassroomInteraction] = Field(default_factory=list, description="课堂互动设计")

    # 课堂练习
    practice_questions: List[PracticeQuestion] = Field(default_factory=list, description="课堂练习题")

    # 作业
    homework: List[HomeworkTask] = Field(default_factory=list, description="作业设计")

    # 板书
    blackboard: Optional[BlackboardDesign] = Field(default=None, description="板书设计")

    # 课堂小结
    summary: str = Field(default="", description="课堂小结")
