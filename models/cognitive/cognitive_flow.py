"""
Cognitive Flow - 认知推进路线

AI 对学生认知状态变化的深层理解。
这是 Cognitive IR 的核心组件。

LangGraph Best Practice:
- 这是 AI 内部结构，不是教师直接阅读的文档
- Renderer 会将其转换为教师可读的教学流程
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class StudentAnalysis(BaseModel):
    """学情分析（AI 内部）"""
    level: str = Field(default="", description="学生水平")
    characteristics: str = Field(default="", description="学生特点")


class TeachingObjectives(BaseModel):
    """教学目标（AI 内部）"""
    cognitive: List[str] = Field(default_factory=list, description="认知目标")
    skill: List[str] = Field(default_factory=list, description="技能目标")
    attitude: List[str] = Field(default_factory=list, description="态度目标")


class CognitiveStage(BaseModel):
    """
    认知阶段（AI 内部）

    这是 AI 对某个教学阶段的认知理解，
    包含认知状态、目标、策略等。

    Renderer 会将其转换为教师可读的教学环节。
    """
    stage_name: str = Field(description="阶段名称，格式：认知状态：认知目标")
    cognitive_state: str = Field(default="", description="学生当前认知状态")
    cognitive_goal: str = Field(default="", description="本阶段认知目标")
    teaching_strategy: str = Field(default="", description="教学策略")
    duration: str = Field(default="", description="建议时长")
    teacher_activity: List[str] = Field(default_factory=list, description="教师活动（具体可视化动作）")
    student_activity: List[str] = Field(default_factory=list, description="学生活动")
    expected_cognitive_change: str = Field(default="", description="预期认知变化")


class CognitiveFlow(BaseModel):
    """
    认知推进路线（AI 内部）

    这是 planner_node 的核心输出，
    代表 AI 对整节课认知推进的完整理解。

    Renderer 会将其转换为教师可读的教学流程。
    """
    lesson_overview: str = Field(description="认知主线（100字以内）")
    lesson_duration: str = Field(default="45分钟", description="课时时长")
    student_analysis: Optional[StudentAnalysis] = Field(default=None, description="学情分析")
    teaching_objectives: Optional[TeachingObjectives] = Field(default=None, description="教学目标")
    cognitive_progression: List[str] = Field(default_factory=list, description="认知递进路径")
    stages: List[CognitiveStage] = Field(default_factory=list, description="认知阶段设计")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "lesson_overview": "通过认知冲突→规律发现→模型建构的路径，帮助学生理解网络分层的必要性",
                    "lesson_duration": "45分钟",
                    "cognitive_progression": [
                        "学生初始状态：认为通信就是直接发送",
                        "阶段1后：意识到通信会冲突",
                        "阶段2后：理解需要规则",
                        "最终状态：建立分层模型的整体认知"
                    ],
                    "stages": [
                        {
                            "stage_name": "认知冲突：为什么网络通信不能乱来",
                            "cognitive_state": "学生认为通信很简单",
                            "cognitive_goal": "激发认知冲突",
                            "teaching_strategy": "认知冲突",
                            "duration": "8分钟",
                            "teacher_activity": ["播放混乱动画", "展示抓包截图"],
                            "student_activity": ["观察动画", "尝试回答"],
                            "expected_cognitive_change": "从认为简单到意识到需要规则"
                        }
                    ]
                }
            ]
        }
