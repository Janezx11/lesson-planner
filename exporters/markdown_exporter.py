"""
markdown_exporter - Markdown 导出器

将 TeacherRuntimePlan 导出为 Markdown 文件。
"""

from models.runtime import TeacherRuntimePlan
from renderers.markdown_renderer import render_markdown


def export_to_markdown(plan: TeacherRuntimePlan, output_path: str) -> str:
    """
    将 TeacherRuntimePlan 导出为 Markdown 文件。

    Args:
        plan: 教师运行时教案
        output_path: 输出文件路径（如 outputs/lesson_plan.md）

    Returns:
        实际写入的文件路径
    """
    md_content = render_markdown(plan)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return output_path
