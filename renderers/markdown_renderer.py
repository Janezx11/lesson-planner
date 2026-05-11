"""
Markdown Renderer - Markdown 渲染器

将 TeacherLessonPlan 转换为 Markdown 格式。

关键原则：
- 不调用 LLM（确定性转换）
- 基于 TeacherLessonPlan，不直接依赖 Cognitive IR
- 输出可直接阅读的 Markdown 文本
"""

from models.teacher import TeacherLessonPlan


def render_markdown(plan: TeacherLessonPlan) -> str:
    """
    将 TeacherLessonPlan 转换为 Markdown 格式

    Args:
        plan: 教师可读的教案

    Returns:
        str: Markdown 格式的教案文本
    """
    lines = []

    # 1. 标题
    lines.append(f"# {plan.header.topic or '教学教案'}")
    lines.append("")

    # 2. 基本信息
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"| 项目 | 内容 |")
    lines.append(f"|------|------|")
    lines.append(f"| 课题 | {plan.header.topic or '待填写'} |")
    lines.append(f"| 年级 | {plan.header.grade or '待填写'} |")
    if plan.header.subject:
        lines.append(f"| 学科 | {plan.header.subject} |")
    lines.append(f"| 课时 | {plan.header.duration} |")
    if plan.header.teaching_methods:
        lines.append(f"| 教学方法 | {'、'.join(plan.header.teaching_methods)} |")
    if plan.header.teaching_tools:
        lines.append(f"| 教学工具 | {'、'.join(plan.header.teaching_tools)} |")
    lines.append("")

    # 3. 教学目标
    if plan.header.teaching_objectives:
        lines.append("## 教学目标")
        lines.append("")
        for i, obj in enumerate(plan.header.teaching_objectives, 1):
            lines.append(f"{i}. {obj}")
        lines.append("")

    # 4. 教学重点难点
    if plan.header.key_points or plan.header.difficult_points:
        lines.append("## 教学重点与难点")
        lines.append("")
        if plan.header.key_points:
            lines.append("**教学重点：**")
            for point in plan.header.key_points:
                lines.append(f"- {point}")
            lines.append("")
        if plan.header.difficult_points:
            lines.append("**教学难点：**")
            for point in plan.header.difficult_points:
                lines.append(f"- {point}")
            lines.append("")

    # 5. 教学过程
    if plan.sections:
        lines.append("## 教学过程")
        lines.append("")
        for i, section in enumerate(plan.sections, 1):
            lines.append(f"### {i}. {section.title}")
            lines.append("")
            if section.duration:
                lines.append(f"**建议时长：** {section.duration}")
                lines.append("")
            lines.append(f"**教师活动：** {section.teacher_activity}")
            lines.append("")
            lines.append(f"**学生活动：** {section.student_activity}")
            lines.append("")
            if section.design_intent:
                lines.append(f"**设计意图：** {section.design_intent}")
                lines.append("")

    # 6. 课堂练习
    if plan.practice:
        lines.append("## 课堂练习")
        lines.append("")
        for i, (q, a) in enumerate(zip(plan.practice.questions, plan.practice.answers), 1):
            lines.append(f"**题目{i}：** {q}")
            lines.append("")
            lines.append(f"**参考答案：** {a}")
            lines.append("")

    # 7. 课堂小结
    if plan.summary:
        lines.append("## 课堂小结")
        lines.append("")
        lines.append(plan.summary)
        lines.append("")

    # 8. 作业布置
    if plan.homework:
        lines.append("## 作业布置")
        lines.append("")
        for hw in plan.homework:
            lines.append(f"**{hw.type}：** {hw.content}")
            if hw.purpose:
                lines.append(f"  - 目的：{hw.purpose}")
            lines.append("")

    # 9. 板书设计
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

    # 10. 教学反思
    if plan.reflection:
        lines.append("## 教学反思")
        lines.append("")
        lines.append(plan.reflection)
        lines.append("")

    return "\n".join(lines)
