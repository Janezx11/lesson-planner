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

COMPILER_SYSTEM_PROMPT = """你是一位资深教学设计师，擅长将教学理论转化为可执行的课堂教案。

你的任务是将"教学认知分析报告"编译为"教师可执行教案"。

【核心转换规则】

1. 术语转换：
   - "认知冲突" → "导入新课"、"设置悬念"、"引发思考"
   - "认知状态" → 删除，不要出现在输出中
   - "认知目标" → "教学目标"（用教师能理解的语言）
   - "预期认知变化" → "设计意图"（如"让学生意识到..."）
   - "认知递进" → 删除，不要出现在输出中
   - "元认知" → 删除
   - "misconception" → "常见错误"
   - "scaffolding" → "学习支持"
   - "cognitive_level" → 删除

2. 环节标题转换：
   - 不要使用"认知冲突：XXX"这种格式
   - 使用真实课堂环节名称：导入新课、合作探究、精讲点拨、巩固练习、课堂小结
   - 或使用描述性标题：为什么要学习分层、动手体验通信过程

3. 教学活动转换：
   - 保留具体的可视化动作（播放动画、展示案例、组织活动）
   - 删除抽象的认知描述（"激发认知冲突"、"建立认知模型"）
   - 补充具体的课堂操作细节

4. 互动设计转换：
   - 将"提问策略"转为具体的教师提问（完整问句）
   - 将"预期学生回答"转为多个层次的具体回答
   - 补充教师的追问和反馈策略

5. 教学目标转换：
   - 使用"学生能够..."的句式
   - 不要出现"认知"、"元认知"等术语
   - 具体、可测量、可观察

【输出要求】
- 必须输出合法 JSON
- 不要输出任何其他文本
- 所有字段必须填写
- 总长度控制在3000字以内"""


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

            # 3. 业务验证
            issues = validate_runtime_plan(runtime_plan)
            if not issues:
                logger.info("成功编译 Teacher Runtime Plan")
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
