"""
Practice Design - 练习题设计

AI 对练习题的分层设计。
这是 Cognitive IR 的组件之一。

LangGraph Best Practice:
- 这是 AI 内部结构
- Renderer 会将其转换为教师可读的练习题列表
"""

from typing import List
from pydantic import BaseModel, Field


class PracticeQuestion(BaseModel):
    """
    练习题（AI 内部）

    这是 AI 对某道练习题的设计，
    包含题目、答案、考察目标等。

    Renderer 会将其转换为教师可读的练习题格式。
    """
    question: str = Field(description="题目内容")
    answer: str = Field(description="参考答案")
    purpose: str = Field(default="", description="考察目标")
    time: str = Field(default="", description="建议用时")


class PracticeDesign(BaseModel):
    """
    练习题设计（AI 内部，分层）

    这是 content_node 的核心输出之一，
    代表 AI 对练习题的分层设计。

    Renderer 会将其转换为教师可读的练习题列表。
    """
    basic: List[PracticeQuestion] = Field(default_factory=list, description="基础题")
    intermediate: List[PracticeQuestion] = Field(default_factory=list, description="中等题")
    advanced: List[PracticeQuestion] = Field(default_factory=list, description="拓展题")
