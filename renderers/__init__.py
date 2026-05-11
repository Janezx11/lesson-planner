"""
renderers - 渲染层

将 Cognitive IR 转换为教师可读的教案格式。

关键原则：
- Renderer 不调用 LLM（确定性转换）
- 通过规则/template 将 Cognitive IR 转为 TeacherLessonPlan
- 所有 Renderer 基于 TeacherLessonPlan，不直接依赖 Cognitive IR

架构：
    Cognitive IR (AI 内部)
        ↓
    Teacher Renderer (确定性转换)
        ↓
    TeacherLessonPlan (教师可读)
        ↓
    Markdown Renderer / DOCX Renderer (格式化输出)
"""

from .teacher_renderer import render_teacher_lesson_plan
from .markdown_renderer import render_markdown

__all__ = [
    "render_teacher_lesson_plan",
    "render_markdown",
]
