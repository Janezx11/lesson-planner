"""
Markdown Renderer - Markdown 渲染器

将 TeacherRuntimePlan 转换为 Markdown 格式。

关键原则：
- 不调用 LLM（确定性转换）
- 基于 TeacherRuntimePlan，不依赖 Cognitive IR
- 输出可直接阅读的 Markdown 文本
"""

from models.runtime import TeacherRuntimePlan


def render_markdown(plan: TeacherRuntimePlan) -> str:
    """
    将 TeacherRuntimePlan 转换为 Markdown 格式

    Args:
        plan: 教师运行时教案

    Returns:
        str: Markdown 格式的教案文本
    """
    lines = []

    # 1. 标题
    lines.append(f"# {plan.topic or '教学教案'}")
    lines.append("")

    # 2. 基本信息
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"| 项目 | 内容 |")
    lines.append(f"|------|------|")
    lines.append(f"| 课题 | {plan.topic or '待填写'} |")
    lines.append(f"| 年级 | {plan.grade or '待填写'} |")
    lines.append(f"| 课时 | {plan.duration} |")
    if plan.teaching_methods:
        lines.append(f"| 教学方法 | {'、'.join(plan.teaching_methods)} |")
    lines.append("")

    # 3. 教学目标
    if plan.teaching_objectives:
        lines.append("## 教学目标")
        lines.append("")
        for i, obj in enumerate(plan.teaching_objectives, 1):
            lines.append(f"{i}. {obj}")
        lines.append("")

    # 4. 教学重点难点
    if plan.key_points or plan.difficult_points:
        lines.append("## 教学重点与难点")
        lines.append("")
        if plan.key_points:
            lines.append("**教学重点：**")
            for point in plan.key_points:
                lines.append(f"- {point}")
            lines.append("")
        if plan.difficult_points:
            lines.append("**教学难点：**")
            for point in plan.difficult_points:
                lines.append(f"- {point}")
            lines.append("")

    # 5. 教学过程
    if plan.sections:
        lines.append("## 教学过程")
        lines.append("")
        for i, section in enumerate(plan.sections, 1):
            lines.append(f"### {i}. {section.title}")
            lines.append("")
            if section.duration_minutes:
                lines.append(f"**建议时长：** {section.duration_minutes}分钟")
                lines.append("")
            lines.append(f"**教师活动：** {section.teacher_activity}")
            lines.append("")
            lines.append(f"**学生活动：** {section.student_activity}")
            lines.append("")
            if section.interaction_method:
                lines.append(f"**互动方式：** {section.interaction_method}")
                lines.append("")
            if section.teaching_intent:
                lines.append(f"**设计意图：** {section.teaching_intent}")
                lines.append("")

    # 6. 课堂互动
    if plan.interactions:
        lines.append("## 课堂互动设计")
        lines.append("")
        for i, interaction in enumerate(plan.interactions, 1):
            lines.append(f"### 互动{i}")
            lines.append("")
            lines.append(f"**触发时机：** {interaction.trigger}")
            lines.append("")
            lines.append(f"**教师提问：** {interaction.teacher_question}")
            lines.append("")
            if interaction.expected_responses:
                lines.append("**预期学生回答：**")
                for resp in interaction.expected_responses:
                    lines.append(f"- {resp}")
                lines.append("")
            if interaction.teacher_followup:
                lines.append(f"**教师追问：** {interaction.teacher_followup}")
                lines.append("")

    # 7. 课堂练习
    if plan.practice_questions:
        lines.append("## 课堂练习")
        lines.append("")
        for i, q in enumerate(plan.practice_questions, 1):
            lines.append(f"**题目{i}（{q.difficulty}）：** {q.question}")
            lines.append("")
            lines.append(f"**参考答案：** {q.answer}")
            lines.append("")

    # 8. 课堂小结
    if plan.summary:
        lines.append("## 课堂小结")
        lines.append("")
        lines.append(plan.summary)
        lines.append("")

    # 9. 作业布置
    if plan.homework:
        lines.append("## 作业布置")
        lines.append("")
        for hw in plan.homework:
            lines.append(f"**{hw.type}：** {hw.content}")
            if hw.purpose:
                lines.append(f"  - 目的：{hw.purpose}")
            lines.append("")

    # 10. 板书设计
    if plan.blackboard:
        lines.append("## 板书设计")
        lines.append("")
        if plan.blackboard.layout:
            lines.append(f"**布局：** {plan.blackboard.layout}")
            lines.append("")
        if plan.blackboard.main_content:
            lines.append("**主板书：**")
            for item in plan.blackboard.main_content:
                lines.append(f"- {item}")
            lines.append("")
        if plan.blackboard.key_formulas:
            lines.append("**核心公式/概念：**")
            for item in plan.blackboard.key_formulas:
                lines.append(f"- {item}")
            lines.append("")

    return "\n".join(lines)
