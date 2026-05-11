"""
renderers - 渲染层

将 TeacherRuntimePlan 格式化为 Markdown/DOCX。

关键原则：
- Renderer 不调用 LLM（确定性转换）
- Renderer 不理解教学逻辑
- 只负责格式输出

架构：
    TeacherRuntimePlan (由 Compiler 生成)
        ↓
    Markdown Renderer / DOCX Renderer (格式化输出)
        ↓
    Markdown / DOCX / PPT
"""

from .markdown_renderer import render_markdown

__all__ = [
    "render_markdown",
]
