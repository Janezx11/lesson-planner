"""
exporters - 文档导出层

将 TeacherRuntimePlan 导出为各种格式。

职责边界：
- 输入: TeacherRuntimePlan (教师运行时教案)
- 输出: DOCX / Markdown 文件
- 不调用 LLM
- 不处理教学逻辑
- 纯格式转换

为什么 Runtime 直出 DOCX：
- Teacher Runtime 是正式数据结构，Markdown 只是 preview
- DOCX 直出避免 Markdown → DOCX 的信息丢失
- 可以精确控制 Word 格式（表格、样式、字体）
"""

from .docx_exporter import export_to_docx
from .markdown_exporter import export_to_markdown

__all__ = ["export_to_docx", "export_to_markdown"]
