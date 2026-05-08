"""
knowledge_node - 知识结构分析节点

这个节点负责分析教学主题的知识结构，
识别核心概念、易错点和前置知识。
"""

import json
from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph
from utils.parser import safe_parse_json, validate_required_fields
from utils.logger import get_logger
from graph.state import TeachingState, NodeNames
from llm.factory import get_llm_for_state

logger = get_logger(__name__)


def knowledge_node(state: TeachingState) -> TeachingState:
    """
    知识结构分析节点

    Args:
        state: 当前状态

    Returns:
        更新后的状态（包含 knowledge 字段）
    """
    topic = state["topic"]
    grade = state["grade"]
    plan = state.get("plan", {})

    logger.info(f"开始分析知识结构: 主题={topic}, 年级={grade}")

    # 读取 Prompt 模板
    try:
        with open("prompts/knowledge.txt", "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logger.error("未找到 knowledge.txt prompt 文件")
        return _handle_error(state, "Prompt file not found")

    # 构建 Prompt - 使用安全的格式化处理，避免 JSON 中的 {} 冲突
    plan_summary = json.dumps(plan, ensure_ascii=False, indent=2)
    try:
        prompt = prompt_template.format(topic=topic, grade=grade, plan=plan_summary)
    except KeyError as e:
        # 如果遇到格式错误，手动替换关键变量
        prompt = prompt_template.replace('{topic}', topic).replace('{grade}', grade).replace('{plan}', str(plan_summary))

    # 定义期望的 JSON Schema (标准格式，避免 Python 类型序列化问题)
    expected_schema = {
        "type": "object",
        "properties": {
            "core_concepts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "concept": {"type": "string"},
                        "definition": {"type": "string"},
                        "importance": {"type": "string"}
                    },
                    "required": ["concept", "definition", "importance"]
                }
            },
            "common_mistakes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "mistake": {"type": "string"},
                        "cause": {"type": "string"},
                        "solution": {"type": "string"}
                    },
                    "required": ["mistake", "cause", "solution"]
                }
            },
            "prerequisite_knowledge": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "knowledge": {"type": "string"},
                        "description": {"type": "string"},
                        "connection": {"type": "string"}
                    },
                    "required": ["knowledge", "description", "connection"]
                }
            },
            "key_insights": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "insight": {"type": "string"},
                        "explanation": {"type": "string"},
                        "teaching_strategy": {"type": "string"}
                    },
                    "required": ["insight", "explanation", "teaching_strategy"]
                }
            },
            "conceptual_hierarchy": {
                "type": "object",
                "properties": {
                    "basic": {"type": "array", "items": {"type": "string"}},
                    "intermediate": {"type": "array", "items": {"type": "string"}},
                    "advanced": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["basic", "intermediate", "advanced"]
            },
            "learning_difficulties": {"type": "array", "items": {"type": "string"}},
            "critical_thinking_points": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["core_concepts", "common_mistakes", "prerequisite_knowledge", "key_insights", "conceptual_hierarchy", "learning_difficulties", "critical_thinking_points"]
    }

    try:
        # 调用 LLM API（支持多提供商）
        llm_client = get_llm_for_state(state)

        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                knowledge_data = llm_client.generate_structured_output(
                    prompt=prompt,
                    schema=expected_schema,
                    system_prompt="你是一个专业的学科知识分析师，擅长深入剖析知识结构和学习难点。"
                )

                # 验证必需字段
                required_fields = ["core_concepts", "common_mistakes", "prerequisite_knowledge"]
                if validate_required_fields(knowledge_data, required_fields):
                    logger.info("成功生成知识结构分析")
                    # Return new state with provider preserved
                    return {
                        **state,  # Preserve all existing fields
                        "knowledge": knowledge_data
                    }

                logger.warning(f"缺少必需字段，尝试第 {attempt + 1} 次重试")

            except Exception as e:
                logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
                if attempt == max_retries - 1:
                    raise

        # 如果所有尝试都失败，创建默认值
        logger.warning("所有重试都失败，使用默认知识结构")
        knowledge_data = {
            "error": "LLM API 调用失败，使用默认知识结构",
            "core_concepts": [{"concept": "核心概念", "definition": "基础定义", "importance": "高"}],
            "common_mistakes": [{"mistake": "常见错误", "cause": "理解偏差", "solution": "加强练习"}],
            "prerequisite_knowledge": [{"knowledge": "前置知识", "description": "基础知识", "connection": "直接相关"}],
            "key_insights": [{"insight": "关键洞察", "explanation": "深入理解", "teaching_strategy": "实例说明"}],
            "conceptual_hierarchy": {"basic": ["基础"], "intermediate": ["中级"], "advanced": ["高级"]},
            "learning_difficulties": ["理解难点"],
            "critical_thinking_points": ["思辨要点"]
        }
        # Return new state with provider preserved
        return {
            **state,  # Preserve all existing fields
            "knowledge": knowledge_data
        }

    except Exception as e:
        logger.error(f"knowledge_node 执行失败: {e}")
        return _handle_error(state, str(e))


def _handle_error(state: TeachingState, error_msg: str) -> TeachingState:
    """处理错误情况"""
    logger.error(f"knowledge_node 错误: {error_msg}")

    # 创建默认的知识结构
    default_knowledge = {
        "error": error_msg,
        "core_concepts": [],
        "common_mistakes": [],
        "prerequisite_knowledge": [],
        "key_insights": [],
        "conceptual_hierarchy": {
            "basic": [],
            "intermediate": [],
            "advanced": []
        },
        "learning_difficulties": [],
        "critical_thinking_points": []
    }

    # Return new state with provider preserved and error count incremented
    new_state = {
        **state,  # Preserve all existing fields
        "knowledge": default_knowledge,
        "error_count": state["error_count"] + 1
    }

    # 检查是否达到最大重试次数
    if new_state["error_count"] >= state["max_retries"]:
        logger.critical("达到最大重试次数，工作流将终止")

    return new_state


# 注册节点到工作流
def create_knowledge_node():
    """创建 knowledge 节点函数"""
    return knowledge_node