"""UnitPlan — 单元整体计划模型

用于多课时教案的整体规划，确保课时之间的衔接和递进。
"""

from typing import List
from pydantic import BaseModel, Field


class LessonOutline(BaseModel):
    """单课时大纲 — 在单元计划中的简要描述"""

    lesson_number: int = Field(description="第几课时（从 1 开始）")
    title: str = Field(description="课时标题")
    core_content: str = Field(description="本课时核心内容，一句话概括")
    objectives: List[str] = Field(default_factory=list, description="本课时教学目标")
    prerequisites: str = Field(default="", description="前置知识（依赖上一课时的什么内容）")
    duration: str = Field(default="45分钟", description="课时时长")


class UnitPlan(BaseModel):
    """单元计划 — 多课时整体规划"""

    unit_title: str = Field(description="单元标题")
    topic: str = Field(description="教学主题")
    grade: str = Field(description="年级")
    total_lessons: int = Field(description="总课时数")
    unit_objectives: List[str] = Field(default_factory=list, description="单元总目标")
    key_points: List[str] = Field(default_factory=list, description="单元重点")
    difficult_points: List[str] = Field(default_factory=list, description="单元难点")
    lessons: List[LessonOutline] = Field(default_factory=list, description="各课时大纲")
    progression_logic: str = Field(default="", description="课时之间的递进关系说明")
