"""
Misconception Model - 易错点模型

AI 对学生常见错误的分析模型。
这是 Cognitive IR 的组件之一。

LangGraph Best Practice:
- 这是 AI 内部结构
- Renderer 会将其转换为教师可读的易错点提醒
"""

from typing import List
from pydantic import BaseModel, Field


class MisconceptionItem(BaseModel):
    """
    易错点（AI 内部）

    这是 AI 对某个易错点的分析，
    包含错误描述、原因、纠正方法等。

    Renderer 会将其转换为教师可读的易错点提醒。
    """
    mistake: str = Field(description="错误描述")
    frequency: str = Field(default="", description="出现频率")
    cause: str = Field(default="", description="错误原因")
    correction: str = Field(default="", description="纠正方法")
    example: str = Field(default="", description="示例")


class MisconceptionModel(BaseModel):
    """
    易错点模型（AI 内部）

    这是 content_node 的输出之一，
    代表 AI 对学生常见错误的完整分析。

    Renderer 会将其转换为教师可读的易错点提醒。
    """
    items: List[MisconceptionItem] = Field(default_factory=list, description="易错点列表")
