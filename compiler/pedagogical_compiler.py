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
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ValidationError

from utils.logger import get_logger
from llm.base import BaseLLMClient
from models.runtime import TeacherRuntimePlan, ClassroomSection, HomeworkTask
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


class ModifySectionChange(BaseModel):
    """修改某个课堂环节"""
    section_index: int = Field(description="要修改的环节索引（0-based）")
    title: Optional[str] = Field(default=None, description="新标题")
    teacher_activity: Optional[str] = Field(default=None, description="新教师活动")
    student_activity: Optional[str] = Field(default=None, description="新学生活动")
    interaction_method: Optional[str] = Field(default=None, description="新互动方式")
    duration_minutes: Optional[int] = Field(default=None, description="新时长（分钟）")


class AddSectionChange(BaseModel):
    """新增一个课堂环节"""
    after_index: int = Field(description="插入到哪个环节之后（0-based，-1 表示开头）")
    title: str = Field(description="环节标题")
    teacher_activity: str = Field(description="教师活动")
    student_activity: str = Field(description="学生活动")
    interaction_method: str = Field(default="", description="互动方式")
    duration_minutes: int = Field(default=10, description="时长（分钟）")


class ChangeSpec(BaseModel):
    """教案改动规格 — LLM 只输出这个，程序负责合并"""
    modify_sections: List[ModifySectionChange] = Field(default_factory=list, description="修改现有环节")
    add_sections: List[AddSectionChange] = Field(default_factory=list, description="新增环节")
    update_objectives: Optional[List[str]] = Field(default=None, description="替换教学目标（null 表示不改）")
    update_summary: Optional[str] = Field(default=None, description="替换课堂小结（null 表示不改）")
    update_homework: Optional[List[HomeworkTask]] = Field(default=None, description="替换作业（null 表示不改）")
    reason: str = Field(default="", description="改动理由，一句话说明改了什么")


CHANGE_SPEC_SYSTEM_PROMPT = """你是一位资深教学设计师。教师会给你一份教案和改进指令，你需要输出结构化的改动规格（Change Spec）。

【原则】
1. 只输出需要改动的部分，不要输出没变的字段
2. modify_sections 用于修改现有环节，add_sections 用于新增环节
3. 不需要改的字段保持 null 或空列表
4. 禁止使用认知科学术语（认知冲突、cognitive 等）
5. reason 字段用一句话概括你做了什么改动

【常见指令对应】
- "增加互动" → modify_sections 中增加 interaction_method，或 add_sections 新增互动环节
- "练习题太简单" → 不在本次改动范围（练习题由其他模块负责）
- "增加小组讨论" → add_sections 新增一个讨论环节，或 modify_sections 修改某个环节
- "缩短导入" → modify_sections 修改第 0 个环节的 duration_minutes
- "教学目标不清晰" → update_objectives 替换为更清晰的目标"""

REGENERATE_SECTION_SYSTEM_PROMPT = """你是一位资深教学设计师。

你的任务是根据教师的改进指令，重新生成教案中的某一个环节。

【原则】
1. 只重新生成指定的环节，其他环节不要改动
2. 新环节要与上下文自然衔接
3. 禁止使用认知科学术语
4. 只输出被要求重新生成的那一个 section 的 JSON 对象

【输出格式】
只输出一个 JSON 对象，包含：
title, teacher_activity, student_activity, interaction_method, duration_minutes, teaching_intent

不要输出其他内容。"""


def _apply_change_spec(plan: TeacherRuntimePlan, spec: ChangeSpec) -> TeacherRuntimePlan:
    """将 ChangeSpec 程序化应用到教案上。

    未在 spec 中出现的字段保持原样，不依赖 LLM 的"自律"。
    """
    plan_dict = plan.model_dump()

    # 修改现有环节
    for change in spec.modify_sections:
        idx = change.section_index
        if idx < 0 or idx >= len(plan_dict["sections"]):
            logger.warning(f"跳过无效环节索引: {idx}")
            continue
        section = plan_dict["sections"][idx]
        for field in ["title", "teacher_activity", "student_activity", "interaction_method", "duration_minutes"]:
            val = getattr(change, field, None)
            if val is not None:
                section[field] = val

    # 新增环节（按 after_index 排序后插入，避免索引漂移）
    for change in sorted(spec.add_sections, key=lambda c: c.after_index, reverse=True):
        new_section = {
            "title": change.title,
            "teacher_activity": change.teacher_activity,
            "student_activity": change.student_activity,
            "interaction_method": change.interaction_method,
            "duration_minutes": change.duration_minutes,
        }
        insert_at = change.after_index + 1
        if insert_at < 0:
            insert_at = 0
        if insert_at > len(plan_dict["sections"]):
            insert_at = len(plan_dict["sections"])
        plan_dict["sections"].insert(insert_at, new_section)

    # 替换教学目标
    if spec.update_objectives is not None:
        plan_dict["teaching_objectives"] = spec.update_objectives

    # 替换课堂小结
    if spec.update_summary is not None:
        plan_dict["summary"] = spec.update_summary

    # 替换作业
    if spec.update_homework is not None:
        plan_dict["homework"] = [hw.model_dump() if hasattr(hw, "model_dump") else hw for hw in spec.update_homework]

    # 清除认知术语
    cleaned = _scrub_plan_recursively(plan_dict)
    return TeacherRuntimePlan(**cleaned)


def improve_existing_plan(
    existing_plan: TeacherRuntimePlan,
    instructions: str,
    topic: str,
    grade: str,
    llm_client: BaseLLMClient,
) -> TeacherRuntimePlan:
    """根据教师指令改进现有教案（Change Spec 方案）。

    LLM 只输出结构化的改动规格，程序负责合并。
    未改动的字段由程序保证不变。

    Args:
        existing_plan: 现有教案
        instructions: 改进指令（如"增加互动环节"、"练习题太简单"）
        topic: 教学主题
        grade: 年级
        llm_client: LLM 客户端

    Returns:
        改进后的 TeacherRuntimePlan
    """
    logger.info(f"开始改进教案: 主题={topic}, 指令={instructions[:50]}")

    plan_json = json.dumps(existing_plan.model_dump(), ensure_ascii=False, indent=2)
    section_list = "\n".join(
        f"  [{i}] {s.title}（{s.duration_minutes or 0}分钟）"
        for i, s in enumerate(existing_plan.sections)
    )

    prompt = (
        f"以下是现有教案：\n\n{plan_json}\n\n"
        f"当前环节列表：\n{section_list}\n\n"
        f"教师的改进指令：{instructions}\n\n"
        f"请输出 Change Spec，只包含需要改动的部分。不需要改的字段保持 null 或空列表。"
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            change_spec = llm_client.generate_structured_output_v2(
                prompt=prompt,
                output_model=ChangeSpec,
                system_prompt=CHANGE_SPEC_SYSTEM_PROMPT,
            )

            logger.info(f"Change Spec: {change_spec.reason or '无说明'}")
            if change_spec.modify_sections:
                logger.info(f"  修改环节: {[c.section_index for c in change_spec.modify_sections]}")
            if change_spec.add_sections:
                logger.info(f"  新增环节: {[c.title for c in change_spec.add_sections]}")

            # 程序合并
            improved = _apply_change_spec(existing_plan, change_spec)

            # 验证
            issues = validate_runtime_plan(improved)
            if not issues:
                quality = score_runtime_plan(improved)
                logger.info(f"教案改进完成 — 评分: {quality['total']}/{quality['max']} ({quality['grade']})")
                return improved
            else:
                logger.warning(f"改进后验证未通过 (尝试 {attempt + 1}/{max_retries}): {issues}")
                if attempt == max_retries - 1:
                    return improved

        except ValidationError as e:
            logger.warning(f"Pydantic 验证失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return existing_plan

        except Exception as e:
            logger.warning(f"改进尝试 {attempt + 1} 失败: {e}")
            if attempt == max_retries - 1:
                raise

    return existing_plan


def regenerate_section(
    existing_plan: TeacherRuntimePlan,
    section_index: int,
    instructions: str,
    llm_client: BaseLLMClient,
) -> TeacherRuntimePlan:
    """重新生成教案中的指定环节。

    程序合并：LLM 只输出新环节，程序将其 splice 回原计划。
    不信任 LLM 全局保持其他字段不变。

    Args:
        existing_plan: 现有教案
        section_index: 要重新生成的环节索引（0-based）
        instructions: 改进指令
        llm_client: LLM 客户端

    Returns:
        更新后的 TeacherRuntimePlan（只有指定环节变化）
    """
    if section_index < 0 or section_index >= len(existing_plan.sections):
        logger.warning(f"无效的环节索引: {section_index}，共 {len(existing_plan.sections)} 个环节")
        return existing_plan

    old_section = existing_plan.sections[section_index]
    logger.info(f"重新生成环节 {section_index}: {old_section.title}")

    # 构建上下文：前一环节和后一环节的标题
    context_parts = []
    if section_index > 0:
        prev = existing_plan.sections[section_index - 1]
        context_parts.append(f"前一环节: {prev.title}")
    context_parts.append(f"当前环节: {old_section.title}")
    if section_index < len(existing_plan.sections) - 1:
        nxt = existing_plan.sections[section_index + 1]
        context_parts.append(f"后一环节: {nxt.title}")

    plan_json = json.dumps(existing_plan.model_dump(), ensure_ascii=False, indent=2)

    prompt = (
        f"以下是完整教案（JSON 格式）：\n\n{plan_json}\n\n"
        f"上下文：{'，'.join(context_parts)}\n\n"
        f"教师的改进指令：{instructions}\n\n"
        f"请只重新生成第 {section_index + 1} 个环节（{old_section.title}），"
        f"输出该环节的 JSON 对象。不要输出其他环节。"
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            new_section = llm_client.generate_structured_output_v2(
                prompt=prompt,
                output_model=ClassroomSection,
                system_prompt=REGENERATE_SECTION_SYSTEM_PROMPT,
            )

            # 程序合并：替换指定环节，其他保持不变
            plan_dict = existing_plan.model_dump()
            plan_dict["sections"][section_index] = new_section.model_dump()

            # 清除认知术语
            cleaned = _scrub_plan_recursively(plan_dict)
            result = TeacherRuntimePlan(**cleaned)

            logger.info(f"环节 {section_index} 已重新生成: {old_section.title} → {new_section.title}")
            return result

        except ValidationError as e:
            logger.warning(f"环节验证失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return existing_plan

        except Exception as e:
            logger.warning(f"重新生成尝试 {attempt + 1} 失败: {e}")
            if attempt == max_retries - 1:
                raise

    return existing_plan


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
