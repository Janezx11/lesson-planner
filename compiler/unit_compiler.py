"""单元计划编译器 — 多课时整体规划 + 逐课时生成

流程：
1. generate_unit_plan() — 用 LLM 生成单元整体规划
2. generate_unit_lessons() — 逐课时生成，每课时注入单元上下文 + 前一课时摘要
"""

import json
from typing import Dict, Any, List, Optional

from utils.logger import get_logger
from llm.base import BaseLLMClient
from models.runtime import UnitPlan, LessonOutline, TeacherRuntimePlan

logger = get_logger(__name__)

UNIT_PLAN_SYSTEM_PROMPT = """你是一位资深教学设计师，擅长做单元整体教学规划。

你的任务是根据教学主题和课时数，规划一个完整的教学单元。

【原则】
1. 每课时有明确的核心内容和目标，课时之间有递进关系
2. 第一课时是基础铺垫，后续课时逐步深入
3. 最后一课时通常是总结提升或综合应用
4. prerequisites 字段说明本课时依赖上一课时的什么内容
5. 禁止使用认知科学术语（认知冲突、cognitive 等）
6. progression_logic 要清晰说明课时之间的逻辑关系

【输出要求】
- 合法 JSON
- lessons 数量必须等于 total_lessons
- 每个 lesson 的 objectives 至少 2 条"""


UNIT_LESSON_CONTEXT_TEMPLATE = """你正在为以下单元生成第 {lesson_number}/{total_lessons} 课时的教案。

【单元信息】
单元标题：{unit_title}
单元目标：{unit_objectives}
课时递进关系：{progression_logic}

【当前课时大纲】
标题：{lesson_title}
核心内容：{core_content}
目标：{lesson_objectives}
前置知识：{prerequisites}
时长：{duration}

{previous_lesson_context}

请根据以上信息，生成完整的教师运行时教案。"""


def generate_unit_plan(
    topic: str,
    grade: str,
    total_lessons: int,
    duration: str,
    level: str,
    llm_client: BaseLLMClient,
) -> UnitPlan:
    """生成单元整体计划。

    Args:
        topic: 教学主题
        grade: 年级
        total_lessons: 总课时数
        duration: 每课时时长
        level: 班级水平
        llm_client: LLM 客户端

    Returns:
        UnitPlan 对象
    """
    logger.info(f"开始生成单元计划: 主题={topic}, 课时数={total_lessons}")

    prompt = (
        f"教学主题：{topic}\n"
        f"年级：{grade}\n"
        f"总课时：{total_lessons} 课时\n"
        f"每课时时长：{duration}\n"
        f"班级水平：{level}\n\n"
        f"请规划这个教学单元的整体方案，包括每课时的核心内容和递进关系。"
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            unit_plan = llm_client.generate_structured_output_v2(
                prompt=prompt,
                output_model=UnitPlan,
                system_prompt=UNIT_PLAN_SYSTEM_PROMPT,
            )

            # 基本验证
            if len(unit_plan.lessons) != total_lessons:
                logger.warning(
                    f"课时数不匹配: 期望 {total_lessons}, 实际 {len(unit_plan.lessons)} (尝试 {attempt + 1})"
                )
                if attempt == max_retries - 1:
                    return unit_plan
                continue

            logger.info(f"单元计划生成完成: {unit_plan.unit_title}, {len(unit_plan.lessons)} 个课时")
            return unit_plan

        except Exception as e:
            logger.warning(f"单元计划生成失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise

    return _create_default_unit_plan(topic, grade, total_lessons, duration)


def build_lesson_context(
    unit_plan: UnitPlan,
    lesson_outline: LessonOutline,
    previous_summary: Optional[str] = None,
) -> str:
    """构建单课时的上下文 prompt。

    Args:
        unit_plan: 单元计划
        lesson_outline: 当前课时大纲
        previous_summary: 前一课时的课堂小结（如有）

    Returns:
        注入到课时生成 prompt 中的上下文文本
    """
    previous_context = ""
    if previous_summary and lesson_outline.lesson_number > 1:
        previous_context = (
            f"【上一课时小结】\n{previous_summary}\n\n"
            f"请在此基础上自然衔接，不要重复上一课时已讲过的内容。"
        )

    return UNIT_LESSON_CONTEXT_TEMPLATE.format(
        lesson_number=lesson_outline.lesson_number,
        total_lessons=unit_plan.total_lessons,
        unit_title=unit_plan.unit_title,
        unit_objectives="；".join(unit_plan.unit_objectives),
        progression_logic=unit_plan.progression_logic,
        lesson_title=lesson_outline.title,
        lesson_objectives="；".join(lesson_outline.objectives),
        core_content=lesson_outline.core_content,
        prerequisites=lesson_outline.prerequisites or "无（本课时为起始课时）",
        duration=lesson_outline.duration,
        previous_lesson_context=previous_context,
    )


def validate_unit_coherence(
    unit_plan: UnitPlan,
    lessons: List[TeacherRuntimePlan],
) -> List[str]:
    """校验单元内各课时的连贯性。

    Returns:
        问题列表（空表示通过）
    """
    issues = []

    if len(lessons) != len(unit_plan.lessons):
        issues.append(f"课时数不匹配: 单元计划 {len(unit_plan.lessons)} 个，实际生成 {len(lessons)} 个")

    # 检查课时之间的知识点是否有重叠
    for i in range(len(lessons) - 1):
        current = lessons[i]
        next_plan = lessons[i + 1]
        current_objectives = set(current.teaching_objectives)
        next_objectives = set(next_plan.teaching_objectives)
        overlap = current_objectives & next_objectives
        if overlap:
            issues.append(
                f"课时 {i + 1} 和 {i + 2} 的教学目标有重叠: {overlap}"
            )

    # 检查每课时是否有足够的环节
    for i, lesson in enumerate(lessons):
        if len(lesson.sections) < 2:
            issues.append(f"课时 {i + 1} 只有 {len(lesson.sections)} 个环节，建议至少 2 个")

    return issues


def _create_default_unit_plan(
    topic: str, grade: str, total_lessons: int, duration: str
) -> UnitPlan:
    """创建默认单元计划（错误时使用）"""
    lessons = []
    for i in range(1, total_lessons + 1):
        lessons.append(LessonOutline(
            lesson_number=i,
            title=f"{topic} 第{i}课时",
            core_content=f"{topic}的第{i}部分内容",
            objectives=[f"理解{topic}第{i}部分的核心概念"],
            prerequisites=f"{topic}第{i - 1}课时的内容" if i > 1 else "",
            duration=duration,
        ))

    return UnitPlan(
        unit_title=f"{topic}单元教学",
        topic=topic,
        grade=grade,
        total_lessons=total_lessons,
        unit_objectives=[f"系统掌握{topic}的核心知识"],
        lessons=lessons,
        progression_logic=f"从基础到应用，逐步深入学习{topic}",
    )
