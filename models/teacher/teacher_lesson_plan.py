"""
Teacher Lesson Plan - 教师可读教案

这是教师最终阅读的教案格式。
参考真实学校教案结构：
- 组织教学
- 导入新课
- 讲授新课
- 课堂练习
- 课堂小结
- 作业布置
- 板书设计

这些模型：
- 接近真实教师教案
- 易读
- 可导出 DOCX
- 可渲染 Markdown
- 接近真实学校教案格式
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from .lesson_section import LessonSection, PracticeSection, HomeworkSection


class LessonHeader(BaseModel):
    """
    教案头部信息

    包含教师可读的基本信息：
    - 课题
    - 年级
    - 课时
    - 教学目标
    - 教学重点
    - 教学难点
    """
    topic: str = Field(description="课题名称")
    grade: str = Field(description="年级")
    subject: str = Field(default="", description="学科")
    duration: str = Field(default="45分钟", description="课时")
    teaching_objectives: List[str] = Field(default_factory=list, description="教学目标")
    key_points: List[str] = Field(default_factory=list, description="教学重点")
    difficult_points: List[str] = Field(default_factory=list, description="教学难点")
    teaching_methods: List[str] = Field(default_factory=list, description="教学方法")
    teaching_tools: List[str] = Field(default_factory=list, description="教学工具")


class BlackboardDesign(BaseModel):
    """
    板书设计

    教师可读的板书设计。
    """
    layout: str = Field(default="", description="布局描述")
    main_content: List[str] = Field(default_factory=list, description="主板书内容")
    key_formulas: List[str] = Field(default_factory=list, description="核心公式/概念")
    diagrams: List[str] = Field(default_factory=list, description="图示说明")


class TeacherLessonPlan(BaseModel):
    """
    教师可读教案

    这是教师最终阅读的教案格式。
    参考真实学校教案结构。

    可以：
    - 直接阅读
    - 导出 DOCX
    - 渲染 Markdown
    - 打印使用
    """
    header: LessonHeader = Field(description="教案头部信息")
    sections: List[LessonSection] = Field(default_factory=list, description="教学环节列表")
    practice: Optional[PracticeSection] = Field(default=None, description="课堂练习")
    homework: List[HomeworkSection] = Field(default_factory=list, description="作业布置")
    blackboard: Optional[BlackboardDesign] = Field(default=None, description="板书设计")
    summary: str = Field(default="", description="课堂小结")
    reflection: str = Field(default="", description="教学反思（预留）")
