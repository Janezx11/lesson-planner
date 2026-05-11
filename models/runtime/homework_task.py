"""
HomeworkTask - 作业任务模型
"""

from pydantic import BaseModel, Field


class HomeworkTask(BaseModel):
    """作业任务"""

    type: str = Field(description="作业类型（必做/选做）")
    content: str = Field(description="作业内容")
    purpose: str = Field(default="", description="作业目的")
