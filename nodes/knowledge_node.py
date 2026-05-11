"""
knowledge_node - 知识结构分析节点

这个节点负责分析教学主题的知识结构，
识别核心概念、易错点和前置知识。

重构说明：
- 删除内联手写 JSON Schema dict
- 使用 Pydantic KnowledgeOutput 作为结构化输出
- 使用 generate_structured_output_v2() 自动校验
"""

import json
from typing import Dict, Any, List
from pydantic import ValidationError
from utils.logger import get_logger
from graph.state import TeachingState
from llm.factory import get_llm_for_state
from models.knowledge import KnowledgeOutput

logger = get_logger(__name__)


def knowledge_node(state: TeachingState) -> Dict[str, Any]:
    """
    知识结构分析节点

    使用 Pydantic Model 作为结构化输出，
    自动校验类型和必填字段。

    返回 partial update: {"knowledge": KnowledgeOutput}
    """
    topic = state.topic
    grade = state.grade
    plan = state.plan

    logger.info(f"开始分析知识结构: 主题={topic}, 年级={grade}")

    # 读取 Prompt 模板
    try:
        with open("prompts/knowledge.txt", "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logger.error("未找到 knowledge.txt prompt 文件")
        return _handle_error(state, "Prompt file not found")

    # 构建 Prompt
    plan_summary = json.dumps(plan, ensure_ascii=False, indent=2)
    try:
        prompt = prompt_template.format(topic=topic, grade=grade, plan=plan_summary)
    except KeyError:
        prompt = prompt_template.replace('{topic}', topic).replace('{grade}', grade).replace('{plan}', str(plan_summary))

    try:
        # 调用 LLM API，使用 Pydantic Model 自动校验
        llm_client = get_llm_for_state(state.model_dump())

        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 使用新的 v2 接口，自动从 KnowledgeOutput 生成 schema
                knowledge_output = llm_client.generate_structured_output_v2(
                    prompt=prompt,
                    output_model=KnowledgeOutput,
                    system_prompt="你是一个专业的学科知识分析师，擅长深入剖析知识结构和学习难点。"
                )

                logger.info("成功生成知识结构分析")
                # 返回 partial update
                return {"knowledge": knowledge_output.model_dump()}

            except ValidationError as e:
                # Pydantic 验证失败
                logger.warning(f"Pydantic 验证失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.warning("达到最大重试次数，使用默认结果")
                    default_output = _create_default_knowledge()
                    return {"knowledge": default_output.model_dump()}

            except Exception as e:
                logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
                if attempt == max_retries - 1:
                    raise

        # 如果所有尝试都失败，创建默认值
        logger.warning("所有重试都失败，使用默认知识结构")
        default_output = _create_default_knowledge()
        return {"knowledge": default_output.model_dump()}

    except Exception as e:
        logger.error(f"knowledge_node 执行失败: {e}")
        return _handle_error(state, str(e))


def _create_default_knowledge() -> KnowledgeOutput:
    """创建默认的知识结构"""
    from models.knowledge import (
        CoreConcept, CommonMistake, PrerequisiteKnowledge,
        KeyInsight, ConceptualHierarchy
    )

    return KnowledgeOutput(
        core_concepts=[
            CoreConcept(concept="核心概念", definition="基础定义", importance="高")
        ],
        common_mistakes=[
            CommonMistake(mistake="常见错误", cause="理解偏差", solution="加强练习")
        ],
        prerequisite_knowledge=[
            PrerequisiteKnowledge(knowledge="前置知识", description="基础知识", connection="直接相关")
        ],
        key_insights=[
            KeyInsight(insight="关键洞察", explanation="深入理解", teaching_strategy="实例说明")
        ],
        conceptual_hierarchy=ConceptualHierarchy(
            basic=["基础"],
            intermediate=["中级"],
            advanced=["高级"]
        ),
        learning_difficulties=["理解难点"],
        critical_thinking_points=["思辨要点"]
    )


def _handle_error(state: TeachingState, error_msg: str) -> Dict[str, Any]:
    """
    处理错误情况

    返回 partial update
    """
    logger.error(f"knowledge_node 错误: {error_msg}")

    default_output = _create_default_knowledge()
    return {
        "knowledge": default_output.model_dump(),
        "error_count": state.error_count + 1
    }


# 注册节点到工作流
def create_knowledge_node():
    """创建 knowledge 节点函数"""
    return knowledge_node
