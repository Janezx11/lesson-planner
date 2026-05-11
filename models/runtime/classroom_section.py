"""
ClassroomSection - 课堂环节模型

接近真实教案的环节描述，不使用认知科学术语。
"""

from typing import Optional
from pydantic import BaseModel, Field


class ClassroomSection(BaseModel):
    """课堂环节 — 接近真实教案的环节描述"""

    title: str = Field(description="环节标题（如'导入新课'、'合作探究'、'巩固练习'）")
    teacher_activity: str = Field(description="教师做什么（具体可操作的动作）")
    student_activity: str = Field(description="学生做什么")
    interaction_method: str = Field(default="", description="互动方式（提问/讨论/演示/练习/小组合作）")
    duration_minutes: Optional[int] = Field(default=None, description="建议时长（分钟）")
    teaching_intent: str = Field(default="", description="设计意图（用教师能理解的语言）")
