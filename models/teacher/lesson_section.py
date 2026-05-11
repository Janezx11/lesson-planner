"""
Lesson Section - 教学环节

教师可读的教学环节描述。
参考真实学校教案格式。
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class LessonSection(BaseModel):
    """
    教学环节

    这是教师可读的教学环节描述，
    接近真实学校教案的格式。

    包含：
    - 环节标题（如"导入新课"、"讲授新课"）
    - 教师活动
    - 学生活动
    - 设计意图
    - 建议时长
    """
    title: str = Field(description="环节标题")
    teacher_activity: str = Field(description="教师活动（具体可操作的描述）")
    student_activity: str = Field(description="学生活动")
    design_intent: str = Field(default="", description="设计意图")
    duration: Optional[str] = Field(default=None, description="建议时长")


class PracticeSection(BaseModel):
    """
    练习环节

    教师可读的练习题描述。
    """
    level: str = Field(description="难度层次（基础/中等/拓展）")
    questions: List[str] = Field(default_factory=list, description="题目列表")
    answers: List[str] = Field(default_factory=list, description="参考答案")
    purpose: str = Field(default="", description="练习目的")


class HomeworkSection(BaseModel):
    """
    作业环节

    教师可读的作业描述。
    """
    type: str = Field(description="作业类型（必做/选做）")
    content: str = Field(description="作业内容")
    purpose: str = Field(default="", description="作业目的")
