"""
formatter_node - 最终输出整合节点

职责：整合所有节点的输出，生成最终的教学方案
- 不再调用 LLM，直接整合已有数据
- 确保输出格式一致
- 添加元数据和统计信息

输入：plan（骨架）+ knowledge（知识）+ design（互动）+ content（内容）
输出：最终教学方案
"""

import datetime
import json
from typing import Dict, Any, List
from utils.logger import get_logger
from graph.state import TeachingState

logger = get_logger(__name__)


def formatter_node(state: TeachingState) -> TeachingState:
    """
    最终输出整合节点

    直接整合所有节点的输出，不再调用 LLM
    """
    topic = state["topic"]
    grade = state["grade"]
    plan = state.get("plan", {})
    knowledge = state.get("knowledge", {})
    design = state.get("design", {})
    content = state.get("content", {})

    logger.info(f"开始整合最终教学方案: 主题={topic}, 年级={grade}")

    try:
        # 整合所有节点的输出
        final_output = _integrate_outputs(topic, grade, plan, knowledge, design, content)

        logger.info("成功整合最终教学方案")
        return {
            **state,
            "final_output": final_output
        }

    except Exception as e:
        logger.error(f"formatter_node 执行失败: {e}")
        return _handle_error(state, str(e))


def _integrate_outputs(
    topic: str,
    grade: str,
    plan: Dict[str, Any],
    knowledge: Dict[str, Any],
    design: Dict[str, Any],
    content: Dict[str, Any]
) -> Dict[str, Any]:
    """
    整合所有节点的输出

    返回格式统一的最终教学方案
    """
    # 元数据
    metadata = {
        "topic": topic,
        "grade": grade,
        "generated_at": datetime.datetime.now().isoformat(),
        "version": "2.0",
        "total_duration": plan.get("lesson_duration", "45分钟")
    }

    # 课程概述
    lesson_overview = plan.get("lesson_overview", "")

    # 教学目标
    teaching_objectives = plan.get("teaching_objectives", {
        "cognitive": [],
        "skill": [],
        "attitude": []
    })

    # 教学流程（来自 planner_node）
    teaching_process = plan.get("teaching_process", [])

    # 互动设计（来自 design_node）
    interactive_design = design.get("interactive_design", [])
    question_chain = design.get("question_chain", [])
    group_activities = design.get("group_activities", [])
    difficulty_support = design.get("difficulty_support", {})

    # 教学内容（来自 content_node）
    practice_design = content.get("practice_design", {
        "basic": [],
        "intermediate": [],
        "advanced": []
    })
    blackboard_design = content.get("blackboard_design", {
        "layout": "",
        "main_content": [],
        "key_formulas": [],
        "diagrams": []
    })
    homework = content.get("homework", [])
    common_mistakes = content.get("common_mistakes", [])
    teacher_script = content.get("teacher_script", [])

    # 构建最终输出
    final_output = {
        "metadata": metadata,
        "lesson_overview": lesson_overview,
        "teaching_objectives": teaching_objectives,
        "teaching_process": teaching_process,
        "interactive_design": interactive_design,
        "question_chain": question_chain,
        "group_activities": group_activities,
        "difficulty_support": difficulty_support,
        "practice_design": practice_design,
        "blackboard_design": blackboard_design,
        "homework": homework,
        "common_mistakes": common_mistakes,
        "teacher_script": teacher_script
    }

    # 添加知识结构（如果存在）
    if knowledge:
        final_output["knowledge_structure"] = knowledge

    # 添加统计信息
    final_output["statistics"] = _generate_statistics(final_output)

    return final_output


def _generate_statistics(output: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成统计信息
    """
    # 练习题统计
    practice = output.get("practice_design", {})
    basic_count = len(practice.get("basic", []))
    intermediate_count = len(practice.get("intermediate", []))
    advanced_count = len(practice.get("advanced", []))
    total_questions = basic_count + intermediate_count + advanced_count

    # 互动统计
    interactive_count = len(output.get("interactive_design", []))
    question_count = len(output.get("question_chain", []))

    # 作业统计
    homework_count = len(output.get("homework", []))

    # 易错点统计
    mistakes_count = len(output.get("common_mistakes", []))

    return {
        "total_questions": total_questions,
        "basic_questions": basic_count,
        "intermediate_questions": intermediate_count,
        "advanced_questions": advanced_count,
        "interactive_points": interactive_count,
        "question_chain_length": question_count,
        "homework_count": homework_count,
        "common_mistakes_count": mistakes_count
    }


def _handle_error(state: TeachingState, error_msg: str) -> TeachingState:
    """处理错误情况"""
    logger.error(f"formatter_node 错误: {error_msg}")

    # 创建最小化的默认输出
    default_output = {
        "error": error_msg,
        "metadata": {
            "topic": state["topic"],
            "grade": state["grade"],
            "generated_at": datetime.datetime.now().isoformat(),
            "version": "2.0",
            "total_duration": "未知"
        },
        "lesson_overview": "教学方案生成失败，请重试",
        "teaching_objectives": {
            "cognitive": [],
            "skill": [],
            "attitude": []
        },
        "teaching_process": [],
        "interactive_design": [],
        "question_chain": [],
        "practice_design": {
            "basic": [],
            "intermediate": [],
            "advanced": []
        },
        "blackboard_design": {
            "layout": "",
            "main_content": [],
            "key_formulas": [],
            "diagrams": []
        },
        "homework": [],
        "common_mistakes": [],
        "statistics": {
            "total_questions": 0,
            "basic_questions": 0,
            "intermediate_questions": 0,
            "advanced_questions": 0,
            "interactive_points": 0,
            "question_chain_length": 0,
            "homework_count": 0,
            "common_mistakes_count": 0
        }
    }

    new_state = {
        **state,
        "final_output": default_output,
        "error_count": state["error_count"] + 1
    }

    if new_state["error_count"] >= state["max_retries"]:
        logger.critical("达到最大重试次数，工作流将终止")

    return new_state


# 注册节点到工作流
def create_formatter_node():
    """创建 formatter 节点函数"""
    return formatter_node
