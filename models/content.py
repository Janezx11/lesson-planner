"""
content_node 输出的 Pydantic Model

替代手写 _get_content_schema() JSON Schema dict。
Pydantic Model 自动生成 JSON Schema，保证类型安全。
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class PracticeQuestion(BaseModel):
    """练习题"""
    question: str = Field(description="题目内容")
    answer: str = Field(description="参考答案")
    purpose: str = Field(default="", description="考察目标")
    time: str = Field(default="", description="建议用时")


class PracticeDesign(BaseModel):
    """练习题设计（分层）"""
    basic: List[PracticeQuestion] = Field(default_factory=list, description="基础题")
    intermediate: List[PracticeQuestion] = Field(default_factory=list, description="中等题")
    advanced: List[PracticeQuestion] = Field(default_factory=list, description="拓展题")


class BlackboardDesign(BaseModel):
    """板书设计"""
    layout: str = Field(default="", description="布局描述")
    main_content: List[str] = Field(default_factory=list, description="主板书内容")
    key_formulas: List[str] = Field(default_factory=list, description="核心公式/概念")
    diagrams: List[str] = Field(default_factory=list, description="图示说明")


class HomeworkItem(BaseModel):
    """作业项"""
    type: str = Field(description="作业类型（必做/选做）")
    content: str = Field(description="作业内容")
    purpose: str = Field(default="", description="作业目的")


class ContentMistake(BaseModel):
    """易错点"""
    mistake: str = Field(description="错误描述")
    frequency: str = Field(default="", description="出现频率")
    cause: str = Field(default="", description="错误原因")
    correction: str = Field(default="", description="纠正方法")
    example: str = Field(default="", description="示例")


class TeacherScript(BaseModel):
    """教师话术"""
    stage: str = Field(description="教学阶段")
    script: str = Field(description="话术内容")


class ContentExample(BaseModel):
    """教学案例"""
    title: str = Field(description="案例标题")
    content: str = Field(description="案例内容")
    explanation: str = Field(default="", description="案例解释")


class ContentOutput(BaseModel):
    """content_node 的结构化输出"""

    practice_design: PracticeDesign = Field(
        default_factory=PracticeDesign,
        description="练习题设计"
    )
    blackboard_design: BlackboardDesign = Field(
        default_factory=BlackboardDesign,
        description="板书设计"
    )
    homework: List[HomeworkItem] = Field(default_factory=list, description="作业设计")
    common_mistakes: List[ContentMistake] = Field(default_factory=list, description="易错点分析")
    teacher_script: List[TeacherScript] = Field(default_factory=list, description="教师话术")
    examples: List[ContentExample] = Field(default_factory=list, description="教学案例")
