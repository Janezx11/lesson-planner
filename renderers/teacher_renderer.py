"""
Teacher Renderer - 教案渲染器

将 Cognitive IR 转换为教师可读的教案格式。

关键原则：
- 不调用 LLM（确定性转换）
- 通过规则/template 将 Cognitive IR 转为 TeacherLessonPlan
- 保证输出格式一致

这是整个项目最重要的渲染器。
"""

from typing import Dict, Any, List

from models.teacher import (
    TeacherLessonPlan,
    LessonHeader,
    LessonSection,
    PracticeSection,
    HomeworkSection,
    BlackboardDesign,
)
from models.cognitive import (
    CognitiveFlow,
    KnowledgeStructure,
    InteractionDesign,
    PracticeDesign,
    MisconceptionModel,
)


def render_teacher_lesson_plan(
    cognitive_flow: Dict[str, Any],
    knowledge_structure: Dict[str, Any] = None,
    interaction_design: Dict[str, Any] = None,
    practice_design: Dict[str, Any] = None,
    misconception_model: Dict[str, Any] = None,
    blackboard_design: Dict[str, Any] = None,
    homework: List[Dict[str, Any]] = None,
    topic: str = "",
    grade: str = "",
) -> TeacherLessonPlan:
    """
    将 Cognitive IR 转换为教师可读的教案

    这是一个确定性转换，不依赖 LLM。

    Args:
        cognitive_flow: 认知推进路线（planner_node 输出）
        knowledge_structure: 知识结构（knowledge_node 输出）
        interaction_design: 互动设计（design_node 输出）
        practice_design: 练习题设计（content_node 输出）
        misconception_model: 易错点模型（content_node 输出）
        blackboard_design: 板书设计（content_node 输出）
        homework: 作业设计（content_node 输出）

    Returns:
        TeacherLessonPlan: 教师可读的教案
    """
    # 1. 渲染教案头部
    header = _render_header(cognitive_flow, topic, grade)

    # 2. 渲染教学环节
    sections = _render_sections(cognitive_flow, interaction_design)

    # 3. 渲染课堂练习
    practice = _render_practice(practice_design)

    # 4. 渲染作业
    homework_sections = _render_homework(homework)

    # 5. 渲染板书设计
    blackboard = _render_blackboard(blackboard_design)

    # 6. 生成课堂小结
    summary = _render_summary(cognitive_flow)

    return TeacherLessonPlan(
        header=header,
        sections=sections,
        practice=practice,
        homework=homework_sections,
        blackboard=blackboard,
        summary=summary,
    )


def _render_header(cognitive_flow: Dict[str, Any], topic: str = "", grade: str = "") -> LessonHeader:
    """渲染教案头部"""
    # 从认知路线提取教学目标
    teaching_objectives = []
    objectives = cognitive_flow.get("teaching_objectives", {})
    if objectives:
        teaching_objectives.extend(objectives.get("cognitive", []))
        teaching_objectives.extend(objectives.get("skill", []))
        teaching_objectives.extend(objectives.get("attitude", []))

    # 如果没有明确的目标，从认知主线提取
    if not teaching_objectives:
        overview = cognitive_flow.get("lesson_overview", "")
        if overview:
            teaching_objectives.append(overview)

    # 提取教学重点（从核心概念）
    key_points = []
    for stage in cognitive_flow.get("stages", []):
        goal = stage.get("cognitive_goal", "")
        if goal and goal not in key_points:
            key_points.append(goal)

    # 提取教学难点（从预期认知变化）
    difficult_points = []
    for stage in cognitive_flow.get("stages", []):
        change = stage.get("expected_cognitive_change", "")
        if change and change not in difficult_points:
            difficult_points.append(change)

    return LessonHeader(
        topic=topic,
        grade=grade,
        duration=cognitive_flow.get("lesson_duration", "45分钟"),
        teaching_objectives=teaching_objectives[:5],  # 最多5个目标
        key_points=key_points[:3],  # 最多3个重点
        difficult_points=difficult_points[:3],  # 最多3个难点
    )


def _render_sections(
    cognitive_flow: Dict[str, Any],
    interaction_design: Dict[str, Any] = None,
) -> List[LessonSection]:
    """渲染教学环节"""
    sections = []

    # 从认知阶段创建教学环节
    stages = cognitive_flow.get("stages", [])
    for i, stage in enumerate(stages):
        # 确定环节标题
        stage_name = stage.get("stage_name", f"环节{i+1}")
        # 提取冒号后面的部分作为标题
        if "：" in stage_name:
            title = stage_name.split("：", 1)[1]
        elif ":" in stage_name:
            title = stage_name.split(":", 1)[1]
        else:
            title = stage_name

        # 渲染教师活动
        teacher_activities = stage.get("teacher_activity", [])
        teacher_activity = "；".join(teacher_activities) if teacher_activities else "见教学设计"

        # 渲染学生活动
        student_activities = stage.get("student_activity", [])
        student_activity = "；".join(student_activities) if student_activities else "见教学设计"

        # 设计意图
        design_intent = stage.get("expected_cognitive_change", "")
        if not design_intent:
            design_intent = stage.get("cognitive_goal", "")

        sections.append(LessonSection(
            title=title,
            teacher_activity=teacher_activity,
            student_activity=student_activity,
            design_intent=design_intent,
            duration=stage.get("duration"),
        ))

    return sections


def _render_practice(practice_design: Dict[str, Any] = None) -> PracticeSection:
    """渲染课堂练习"""
    if not practice_design:
        return None

    # 合并所有层次的题目
    all_questions = []
    all_answers = []

    for level in ["basic", "intermediate", "advanced"]:
        questions = practice_design.get(level, [])
        for q in questions:
            all_questions.append(q.get("question", ""))
            all_answers.append(q.get("answer", ""))

    if not all_questions:
        return None

    return PracticeSection(
        level="分层练习",
        questions=all_questions,
        answers=all_answers,
        purpose="巩固课堂所学知识",
    )


def _render_homework(homework: List[Dict[str, Any]] = None) -> List[HomeworkSection]:
    """渲染作业"""
    if not homework:
        return []

    sections = []
    for item in homework:
        sections.append(HomeworkSection(
            type=item.get("type", "必做"),
            content=item.get("content", ""),
            purpose=item.get("purpose", ""),
        ))

    return sections


def _render_blackboard(blackboard_design: Dict[str, Any] = None) -> BlackboardDesign:
    """渲染板书设计"""
    if not blackboard_design:
        return None

    return BlackboardDesign(
        layout=blackboard_design.get("layout", ""),
        main_content=blackboard_design.get("main_content", []),
        key_formulas=blackboard_design.get("key_formulas", []),
        diagrams=blackboard_design.get("diagrams", []),
    )


def _render_summary(cognitive_flow: Dict[str, Any]) -> str:
    """渲染课堂小结"""
    # 从认知递进路径生成小结
    progression = cognitive_flow.get("cognitive_progression", [])
    if not progression:
        return ""

    # 取最后阶段作为小结
    if len(progression) >= 2:
        return f"通过本节课学习，{progression[-1]}"
    elif progression:
        return progression[0]
    else:
        return ""
