"""
models/teacher - 教师可读教案模型

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

from .lesson_section import LessonSection, PracticeSection, HomeworkSection
from .teacher_lesson_plan import (
    TeacherLessonPlan,
    LessonHeader,
    BlackboardDesign,
)

__all__ = [
    "LessonSection",
    "PracticeSection",
    "HomeworkSection",
    "TeacherLessonPlan",
    "LessonHeader",
    "BlackboardDesign",
]
