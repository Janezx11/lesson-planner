"""
PracticeQuestion - 课堂练习题模型
"""

from pydantic import BaseModel, Field


class PracticeQuestion(BaseModel):
    """课堂练习题"""

    question: str = Field(description="题目内容")
    answer: str = Field(description="参考答案")
    purpose: str = Field(default="", description="考察目标")
    difficulty: str = Field(default="基础", description="难度：基础/中等/拓展")
