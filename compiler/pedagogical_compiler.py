"""
pedagogical_compiler - 教学认知编译器核心

将 Cognitive IR 编译为 Teacher Runtime Plan。

使用 LLM 进行语义转换：
- 认知术语 → 教师语言
- 认知阶段 → 课堂环节
- 认知目标 → 教学目标
- 认知策略 → 教学方法

输出强类型 Pydantic Model，不输出自由文本。
"""

import json
from typing import Dict, Any, List
from pydantic import ValidationError

from utils.logger import get_logger
from llm.base import BaseLLMClient
from models.runtime import TeacherRuntimePlan
from compiler.prompt_builder import build_compiler_prompt

logger = get_logger(__name__)

# 认知术语 → 教师友好术语 的自动替换表
_COGNITIVE_TERM_REPLACEMENTS = {
    "认知冲突": "导入新课",
    "认知状态": "",
    "认知目标": "教学目标",
    "预期认知变化": "设计意图",
    "认知递进": "",
    "元认知": "",
    "misconception": "常见错误",
    "Misconception": "常见错误",
    "MISCONCEPTION": "常见错误",
    "scaffolding": "学习支持",
    "Scaffolding": "学习支持",
    "SCAFFOLDING": "学习支持",
    "cognitive": "",
    "Cognitive": "",
    "COGNITIVE": "",
    "认知模型": "知识框架",
    "认知负荷": "学习难度",
    "认知发展": "学习进阶",
}


def _scrub_cognitive_terms(text: str) -> str:
    """自动替换文本中的认知术语为教师友好术语。"""
    result = text
    for term, replacement in _COGNITIVE_TERM_REPLACEMENTS.items():
        result = result.replace(term, replacement)
    return result


def _scrub_plan_recursively(plan_dict: Dict[str, Any]) -> Dict[str, Any]:
    """递归替换 plan 字典中所有字符串字段的认知术语。"""
    cleaned = {}
    for key, value in plan_dict.items():
        if isinstance(value, str):
            cleaned[key] = _scrub_cognitive_terms(value)
        elif isinstance(value, list):
            cleaned[key] = [
                _scrub_plan_recursively(item) if isinstance(item, dict)
                else _scrub_cognitive_terms(item) if isinstance(item, str)
                else item
                for item in value
            ]
        elif isinstance(value, dict):
            cleaned[key] = _scrub_plan_recursively(value)
        else:
            cleaned[key] = value
    return cleaned


COMPILER_SYSTEM_PROMPT = """你是一位资深教学设计师，擅长将教学理论转化为可执行的课堂教案。

你的任务是将"教学认知分析报告"编译为"教师可执行教案"。

【最高优先级 - 禁止术语】
你的输出中绝对不能出现以下词语，违反将导致输出作废：
❌ 禁止：认知冲突、认知状态、认知目标、认知递进、元认知、cognitive、misconception、scaffolding、cognitive_level
✅ 替换为：导入新课、设置悬念、引发思考、教学目标、设计意图、常见错误、学习支持

【核心转换规则】

1. 术语转换：
   - "认知冲突" → "导入新课"、"设置悬念"、"引发思考"
   - "认知状态" → 删除
   - "认知目标" → "教学目标"
   - "预期认知变化" → "设计意图"
   - "认知递进" → 删除
   - "元认知" → 删除
   - "misconception" → "常见错误"
   - "scaffolding" → "学习支持"

2. 环节标题：
   - 使用真实课堂环节名称：导入新课、合作探究、精讲点拨、巩固练习、课堂小结
   - 或描述性标题：为什么要学习分层、动手体验通信过程

3. 教学活动：
   - 保留具体动作（播放动画、展示案例、组织活动）
   - 删除抽象认知描述（"激发认知冲突"、"建立认知模型"）

4. 教学目标：
   - 使用"学生能够..."的句式
   - 具体、可测量、可观察

【字段名称 - 必须严格遵守！】
topic, grade, duration, teaching_methods, teaching_objectives, key_points, difficult_points, sections, interactions, practice_questions, homework, blackboard, summary

sections 每个对象包含: title, teacher_activity, student_activity, interaction_method, duration_minutes, teaching_intent
interactions 每个对象包含: trigger, teacher_question, expected_responses, teacher_followup
practice_questions 每个对象包含: question, answer, purpose, difficulty
homework 每个对象包含: type, content, purpose
blackboard 包含: layout, main_content, key_formulas, diagrams

禁止使用其他字段名！禁止使用中文字段名！

【输出要求】
- 必须输出合法 JSON
- 不要输出任何其他文本
- 所有字段必须填写
- 总长度控制在3000字以内
- 输出前检查：是否包含禁止术语？如有，立即替换！"""


def compile_cognitive_ir(
    cognitive_flow: Dict[str, Any],
    knowledge_structure: Dict[str, Any],
    interaction_design: Dict[str, Any],
    practice_design: Dict[str, Any],
    misconception_model: Dict[str, Any],
    blackboard_design: Dict[str, Any],
    homework: List[Dict[str, Any]],
    topic: str,
    grade: str,
    llm_client: BaseLLMClient,
) -> TeacherRuntimePlan:
    """
    Cognitive IR → Teacher Runtime Plan

    使用 LLM 进行语义转换，输出强类型 Pydantic Model。

    Args:
        cognitive_flow: 认知推进路线（planner_node 输出）
        knowledge_structure: 知识结构（knowledge_node 输出）
        interaction_design: 互动设计（design_node 输出）
        practice_design: 练习题设计（content_node 输出）
        misconception_model: 易错点模型（content_node 输出）
        blackboard_design: 板书设计（content_node 输出）
        homework: 作业设计（content_node 输出）
        topic: 教学主题
        grade: 年级
        llm_client: LLM 客户端

    Returns:
        TeacherRuntimePlan: 教师运行时教案
    """
    logger.info(f"开始编译 Cognitive IR → Teacher Runtime Plan: 主题={topic}")

    # 1. 构建 Prompt
    prompt = build_compiler_prompt(
        cognitive_flow=cognitive_flow,
        knowledge_structure=knowledge_structure,
        interaction_design=interaction_design,
        practice_design=practice_design,
        misconception_model=misconception_model,
        blackboard_design=blackboard_design,
        homework=homework,
        topic=topic,
        grade=grade,
    )

    # 2. 调用 LLM，使用 Structured Output
    max_retries = 3
    for attempt in range(max_retries):
        try:
            runtime_plan = llm_client.generate_structured_output_v2(
                prompt=prompt,
                output_model=TeacherRuntimePlan,
                system_prompt=COMPILER_SYSTEM_PROMPT
            )

            # 3. 后处理：自动清除残留的认知术语
            plan_dict = runtime_plan.model_dump()
            cleaned_dict = _scrub_plan_recursively(plan_dict)
            runtime_plan = TeacherRuntimePlan(**cleaned_dict)

            # 4. 业务验证
            issues = validate_runtime_plan(runtime_plan)
            if not issues:
                quality = score_runtime_plan(runtime_plan)
                logger.info(
                    f"成功编译 Teacher Runtime Plan — 质量评分: {quality['total']}/{quality['max']} ({quality['grade']})"
                )
                if quality["deductions"]:
                    for d in quality["deductions"]:
                        logger.debug(f"  扣分: {d}")
                return runtime_plan
            else:
                logger.warning(f"编译输出验证未通过 (尝试 {attempt + 1}/{max_retries}):")
                for issue in issues:
                    logger.warning(f"  - {issue}")
                if attempt == max_retries - 1:
                    logger.warning("达到最大重试次数，使用当前结果")
                    return runtime_plan

        except ValidationError as e:
            logger.warning(f"Pydantic 验证失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                logger.warning("达到最大重试次数，使用默认结果")
                return _create_default_runtime_plan(topic, grade)

        except Exception as e:
            logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
            if attempt == max_retries - 1:
                raise

    return _create_default_runtime_plan(topic, grade)


def validate_runtime_plan(plan: TeacherRuntimePlan) -> List[str]:
    """验证 TeacherRuntimePlan 的业务规则"""
    issues = []

    if not plan.teaching_objectives:
        issues.append("缺少教学目标")

    if len(plan.sections) < 2:
        issues.append(f"教学环节只有{len(plan.sections)}个，要求至少2个")

    # 检查是否还有认知术语泄露
    cognitive_terms = ["认知冲突", "认知状态", "认知目标", "认知递进", "元认知", "cognitive", "misconception"]
    all_text = json.dumps(plan.model_dump(), ensure_ascii=False)
    for term in cognitive_terms:
        if term in all_text:
            issues.append(f"输出中仍包含认知术语: {term}")

    return issues


def score_runtime_plan(plan: TeacherRuntimePlan) -> Dict[str, Any]:
    """对 TeacherRuntimePlan 进行质量评分。

    Returns:
        评分结果，包含总分和各维度得分。
    """
    scores = {}
    deductions = []

    # 1. 字段完整性 (30分)
    completeness = 30
    if not plan.teaching_objectives:
        completeness -= 10
        deductions.append("缺少教学目标 (-10)")
    if not plan.sections:
        completeness -= 10
        deductions.append("缺少教学环节 (-10)")
    if not plan.homework:
        completeness -= 5
        deductions.append("缺少作业设计 (-5)")
    scores["字段完整性"] = max(0, completeness)

    # 2. 认知术语清洁度 (25分)
    cleanliness = 25
    cognitive_terms = ["认知冲突", "认知状态", "认知目标", "认知递进", "元认知", "cognitive", "misconception", "scaffolding"]
    all_text = json.dumps(plan.model_dump(), ensure_ascii=False).lower()
    for term in cognitive_terms:
        if term.lower() in all_text:
            cleanliness -= 5
            deductions.append(f"残留术语 '{term}' (-5)")
    scores["术语清洁度"] = max(0, cleanliness)

    # 3. 环节时间合理性 (20分)
    time_score = 20
    if plan.sections:
        total_minutes = sum(s.duration_minutes or 0 for s in plan.sections)
        if total_minutes == 0:
            time_score -= 10
            deductions.append("未填写时长 (-10)")
        elif total_minutes < 30:
            time_score -= 5
            deductions.append(f"总时长偏短: {total_minutes}分钟 (-5)")
        if len(plan.sections) < 3:
            time_score -= 5
            deductions.append(f"环节偏少: {len(plan.sections)}个 (-5)")
    scores["时间合理性"] = max(0, time_score)

    # 4. 互动设计 (15分)
    interaction_score = 15
    if not plan.interactions:
        interaction_score -= 10
        deductions.append("缺少互动设计 (-10)")
    elif len(plan.interactions) < 2:
        interaction_score -= 5
        deductions.append(f"互动偏少: {len(plan.interactions)}个 (-5)")
    scores["互动设计"] = max(0, interaction_score)

    # 5. 练习与作业 (10分)
    practice_score = 10
    if not plan.practice_questions:
        practice_score -= 5
        deductions.append("缺少练习题 (-5)")
    if not plan.homework:
        practice_score -= 5
        deductions.append("缺少作业 (-5)")
    scores["练习与作业"] = max(0, practice_score)

    total = sum(scores.values())
    return {
        "total": total,
        "max": 110,
        "scores": scores,
        "deductions": deductions,
        "grade": "优秀" if total >= 90 else "良好" if total >= 75 else "合格" if total >= 60 else "需改进",
    }


def _create_default_runtime_plan(topic: str, grade: str) -> TeacherRuntimePlan:
    """创建默认的运行时教案（错误时使用）"""
    from models.runtime import ClassroomSection, HomeworkTask

    return TeacherRuntimePlan(
        topic=topic,
        grade=grade,
        teaching_objectives=[f"理解{topic}的核心概念"],
        sections=[
            ClassroomSection(
                title="导入新课",
                teacher_activity=f"通过实际案例引入{topic}的学习",
                student_activity="思考并回答问题",
                duration_minutes=10,
            ),
            ClassroomSection(
                title="合作探究",
                teacher_activity="组织学生分组讨论",
                student_activity="小组讨论，总结规律",
                duration_minutes=20,
            ),
            ClassroomSection(
                title="巩固练习",
                teacher_activity="讲解典型例题",
                student_activity="独立完成练习",
                duration_minutes=15,
            ),
        ],
        homework=[
            HomeworkTask(type="必做", content="完成课后练习", purpose="巩固课堂所学"),
        ],
        summary=f"本节课学习了{topic}的核心内容",
    )
