"""
content_node - 教学内容生成节点

职责：根据教学计划骨架和互动设计，生成具体的教学内容
- practice_design: 练习题设计
- blackboard_design: 板书设计
- homework: 作业设计
- teacher_script: 教师话术
- common_mistakes: 易错点分析

输入：planner_node 输出（教学骨架）+ design_node 输出（互动设计）
输出：ContentOutput: 强类型 Pydantic Model

重构说明：
- 删除手写 _get_content_schema() JSON Schema dict
- 使用 Pydantic ContentOutput 作为结构化输出
- 使用 generate_structured_output_v2() 自动校验
"""

import json
from typing import Dict, Any, List
from pydantic import ValidationError
from utils.logger import get_logger
from graph.state import TeachingState
from llm.factory import get_llm_for_state
from models.content import ContentOutput, ContentPracticeDesign, ContentBlackboardDesign
from models.subjects import detect_subject, get_subject_guidance, format_subject_guidance

logger = get_logger(__name__)


def validate_content_output(output: ContentOutput) -> List[str]:
    """
    验证 ContentOutput 的业务规则

    Pydantic 已经保证了类型安全，
    这里只做业务层面的验证。

    返回: 问题列表（空表示通过）
    """
    issues = []

    # 检查 practice_design
    basic_count = len(output.practice_design.basic)
    intermediate_count = len(output.practice_design.intermediate)
    advanced_count = len(output.practice_design.advanced)

    if basic_count < 2:
        issues.append(f"基础题只有{basic_count}道，要求至少2道")
    if intermediate_count < 1:
        issues.append(f"中等题只有{intermediate_count}道，要求至少1道")
    if advanced_count < 1:
        issues.append(f"拓展题只有{advanced_count}道，要求至少1道")

    # 检查 blackboard_design
    if not output.blackboard_design.layout:
        issues.append("blackboard_design缺少layout字段")
    if not output.blackboard_design.main_content:
        issues.append("blackboard_design缺少main_content字段")

    # 检查 homework
    if len(output.homework) < 1:
        issues.append("homework至少需要1道作业")

    return issues


def create_default_content_output() -> ContentOutput:
    """创建默认的教学内容"""
    from models.content import (
        ContentPracticeQuestion, HomeworkItem, ContentMistake
    )

    return ContentOutput(
        practice_design=ContentPracticeDesign(
            basic=[
                ContentPracticeQuestion(question="基础练习题", answer="参考答案", purpose="考察基本概念", time="2分钟"),
                ContentPracticeQuestion(question="基础练习题2", answer="参考答案", purpose="考察基本计算", time="2分钟")
            ],
            intermediate=[
                ContentPracticeQuestion(question="中等练习题", answer="参考答案", purpose="考察应用能力", time="3分钟")
            ],
            advanced=[
                ContentPracticeQuestion(question="拓展练习题", answer="参考答案", purpose="考察综合能力", time="5分钟")
            ]
        ),
        blackboard_design=ContentBlackboardDesign(
            layout="左中右三区布局",
            main_content=["核心概念", "重要公式", "解题步骤"],
            key_formulas=["公式1", "公式2"],
            diagrams=["图示说明"]
        ),
        homework=[
            HomeworkItem(type="必做", content="基础作业", purpose="巩固课堂知识"),
            HomeworkItem(type="选做", content="拓展作业", purpose="提升综合能力")
        ],
        common_mistakes=[
            ContentMistake(
                mistake="典型错误",
                frequency="高",
                cause="概念理解不清",
                correction="强调关键点",
                example="纠正示例"
            )
        ]
    )


def content_node(state: TeachingState) -> Dict[str, Any]:
    """
    教学内容生成节点

    使用 Pydantic Model 作为结构化输出，
    自动校验类型和必填字段。

    返回 partial update: {"content": ContentOutput}
    """
    topic = state.topic
    grade = state.grade
    plan = state.plan
    design = state.design

    logger.info(f"开始生成教学内容: 主题={topic}, 年级={grade}")

    # 学科检测
    subject = detect_subject(topic)
    subject_guidance = get_subject_guidance(subject)
    if subject_guidance:
        logger.info(f"检测到学科: {subject}，注入学科指导")

    # 读取 Prompt 模板
    try:
        with open("prompts/content.txt", "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logger.error("未找到 content.txt prompt 文件")
        return _handle_error(state, "Prompt file not found")

    # 构建 Prompt
    plan_summary = json.dumps(plan, ensure_ascii=False, indent=2)
    design_summary = json.dumps(design, ensure_ascii=False, indent=2)
    prompt = prompt_template.replace('{topic}', topic).replace('{grade}', grade).replace('{plan}', plan_summary).replace('{design}', design_summary)

    try:
        # 调用 LLM API，使用 Pydantic Model 自动校验
        llm_client = get_llm_for_state(state.model_dump())

        sys_prompt = _get_system_prompt(subject_guidance)

        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 使用新的 v2 接口，自动从 ContentOutput 生成 schema
                content_output = llm_client.generate_structured_output_v2(
                    prompt=prompt,
                    output_model=ContentOutput,
                    system_prompt=sys_prompt
                )

                # 业务层面验证
                issues = validate_content_output(content_output)

                if not issues:
                    logger.info("成功生成教学内容")
                    # 返回 partial update
                    return {"content": content_output.model_dump()}
                else:
                    logger.warning(f"输出验证未通过 (尝试 {attempt + 1}/{max_retries}):")
                    for issue in issues:
                        logger.warning(f"  - {issue}")

                    # 如果是最后一次尝试，使用当前结果
                    if attempt == max_retries - 1:
                        logger.warning("达到最大重试次数，使用当前结果")
                        return {"content": content_output.model_dump()}

            except ValidationError as e:
                # Pydantic 验证失败
                logger.warning(f"Pydantic 验证失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.warning("达到最大重试次数，使用默认结果")
                    default_output = create_default_content_output()
                    return {"content": default_output.model_dump()}

            except Exception as e:
                logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
                if attempt == max_retries - 1:
                    raise

        # 如果所有尝试都失败，创建默认值
        logger.warning("所有重试都失败，使用默认教学内容")
        default_output = create_default_content_output()
        return {"content": default_output.model_dump()}

    except Exception as e:
        logger.error(f"content_node 执行失败: {e}")
        return _handle_error(state, str(e))


def _get_system_prompt(subject_guidance=None) -> str:
    """获取系统提示"""
    base = (
        "你是一位经验丰富的教学内容设计师。\n"
        "你的任务是根据教学计划骨架和互动设计，生成具体的教学内容。\n\n"
        "【重要规则】\n"
        "1. practice_design 必须包含分层练习题：basic（基础）、intermediate（中等）、advanced（拓展）\n"
        "2. 每道题必须包含：question（题目）、answer（答案）、purpose（考察目标）、time（建议用时）\n"
        "3. blackboard_design 必须包含：layout（布局）、main_content（主板书）、key_formulas（核心公式）\n"
        "4. homework 必须包含：type（必做/选做）、content（作业内容）、purpose（作业目的）\n"
        "5. 保持输出简洁，总长度控制在3500tokens以内\n"
    )
    if subject_guidance:
        base += f"\n{format_subject_guidance(subject_guidance)}\n"
    return base


def _handle_error(state: TeachingState, error_msg: str) -> Dict[str, Any]:
    """处理错误情况，返回 partial update"""
    logger.error(f"content_node 错误: {error_msg}")

    default_output = create_default_content_output()
    warnings = list(state.warnings) + [f"[content_node] 使用了默认输出: {error_msg}"]
    return {
        "content": default_output.model_dump(),
        "error_count": state.error_count + 1,
        "warnings": warnings,
    }


# 注册节点到工作流
def create_content_node():
    """创建 content 节点函数"""
    return content_node
