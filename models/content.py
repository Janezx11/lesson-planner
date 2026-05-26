"""
content_node 输出的 Pydantic Model

这是 content_node 的 LLM 输出 schema，仅用于 content_node 内部。
与 models/runtime/ 的教师运行时模型是不同的层次。

注意：类名加 Content 前缀以避免与 models/runtime/ 命名冲突。
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ContentPracticeQuestion(BaseModel):
    """content_node 输出的练习题"""
    question: str = Field(description="题目内容")
    answer: str = Field(description="参考答案")
    purpose: str = Field(default="", description="考察目标")
    time: str = Field(default="", description="建议用时")


class ContentPracticeDesign(BaseModel):
    """content_node 输出的练习题设计（分层）"""
    basic: List[ContentPracticeQuestion] = Field(default_factory=list, description="基础题")
    intermediate: List[ContentPracticeQuestion] = Field(default_factory=list, description="中等题")
    advanced: List[ContentPracticeQuestion] = Field(default_factory=list, description="拓展题")


class ContentBlackboardDesign(BaseModel):
    """content_node 输出的板书设计"""
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

    practice_design: ContentPracticeDesign = Field(
        default_factory=ContentPracticeDesign,
        description="练习题设计"
    )
    blackboard_design: ContentBlackboardDesign = Field(
        default_factory=ContentBlackboardDesign,
        description="板书设计"
    )
    homework: List[HomeworkItem] = Field(default_factory=list, description="作业设计")
    common_mistakes: List[ContentMistake] = Field(default_factory=list, description="易错点分析")
    teacher_script: List[TeacherScript] = Field(default_factory=list, description="教师话术")
    examples: List[ContentExample] = Field(default_factory=list, description="教学案例")
