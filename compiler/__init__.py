"""
compiler - 教学认知编译器 (LLM Pedagogical Compiler)

将 Cognitive IR (AI 内部认知结构) 编译为 Teacher Runtime Plan (教师可读教案)。

职责边界：
- 输入: Cognitive IR (认知阶段、知识结构、互动设计等)
- 输出: TeacherRuntimePlan (课堂环节、教学活动、师生互动等)
- 使用 LLM 进行语义转换（不是简单模板替换）
- 输出强类型 Pydantic Model（不是自由文本）

关键原则：
- Compiler 使用 LLM，但输出 Structured Output
- Cognitive IR 中的认知术语不暴露给教师
- 将认知目标转为教师可理解的教学目标
"""

from .pedagogical_compiler import compile_cognitive_ir

__all__ = ["compile_cognitive_ir"]
