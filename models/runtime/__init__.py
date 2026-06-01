"""
models/runtime - 教师运行时模型 (Teacher Runtime Models)

这是最终给教师看的教案结构，不包含任何认知科学术语。

设计原则：
- 接近真实学校教案格式
- 教师可直接理解和执行
- 可导出 DOCX/PDF
- 可渲染 Markdown
- 不暴露 AI 内部认知结构
"""

from .classroom_section import ClassroomSection
from .classroom_interaction import ClassroomInteraction
from .practice_question import PracticeQuestion
from .homework_task import HomeworkTask
from .blackboard_design import BlackboardDesign
from .teacher_runtime_plan import TeacherRuntimePlan
from .unit_plan import UnitPlan, LessonOutline

__all__ = [
    "ClassroomSection",
    "ClassroomInteraction",
    "PracticeQuestion",
    "HomeworkTask",
    "BlackboardDesign",
    "TeacherRuntimePlan",
    "UnitPlan",
    "LessonOutline",
]
