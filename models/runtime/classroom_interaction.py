"""
ClassroomInteraction - 课堂互动模型

具体的师生互动设计，面向真实课堂执行。
"""

from typing import List
from pydantic import BaseModel, Field


class ClassroomInteraction(BaseModel):
    """课堂互动 — 具体的师生互动设计"""

    trigger: str = Field(description="触发时机（如'讲到分层概念时'、'学生完成练习后'）")
    teacher_question: str = Field(description="教师提问（完整问句，可直接在课堂上使用）")
    expected_responses: List[str] = Field(default_factory=list, description="预期学生回答（多个层次）")
    teacher_followup: str = Field(default="", description="教师追问或反馈策略")
