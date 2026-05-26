"""
compiler_node - 教学认知编译节点

职责：
- 读取 Cognitive IR（plan, knowledge, design, content）
- 调用 LLM Pedagogical Compiler
- 输出 Teacher Runtime Plan

架构位置：
    Cognitive IR (planner + knowledge + design + content)
        ↓
    compiler_node (LLM 语义转换)
        ↓
    TeacherRuntimePlan

关键原则：
- 使用 LLM 进行语义转换
- 输出强类型 Pydantic Model
- 不直接输出 Markdown
"""

from typing import Dict, Any
from utils.logger import get_logger
from graph.state import TeachingState
from llm.factory import get_llm_for_state
from compiler.pedagogical_compiler import compile_cognitive_ir

logger = get_logger(__name__)


def compiler_node(state: TeachingState) -> Dict[str, Any]:
    """
    教学认知编译节点

    Cognitive IR → Teacher Runtime Plan (LLM-based)

    返回 partial update: {"runtime": TeacherRuntimePlan dict}
    """
    topic = state.topic
    grade = state.grade
    plan = state.plan
    knowledge = state.knowledge
    design = state.design
    content = state.content

    logger.info(f"开始编译 Cognitive IR → Teacher Runtime Plan: 主题={topic}, 年级={grade}")

    try:
        # 获取 LLM 客户端
        llm_client = get_llm_for_state(state.model_dump())

        # 调用编译器
        runtime_plan = compile_cognitive_ir(
            cognitive_flow=plan,
            knowledge_structure=knowledge,
            interaction_design=design,
            practice_design=content.get("practice_design"),
            misconception_model={"items": content.get("common_mistakes", [])},
            blackboard_design=content.get("blackboard_design"),
            homework=content.get("homework"),
            topic=topic,
            grade=grade,
            llm_client=llm_client,
        )

        logger.info("成功编译 Teacher Runtime Plan")
        return {"runtime": runtime_plan.model_dump()}

    except Exception as e:
        logger.error(f"compiler_node 执行失败: {e}")
        return _handle_error(state, str(e))


def _handle_error(state: TeachingState, error_msg: str) -> Dict[str, Any]:
    """处理错误情况"""
    logger.error(f"compiler_node 错误: {error_msg}")

    from compiler.pedagogical_compiler import _create_default_runtime_plan
    default_plan = _create_default_runtime_plan(state.topic, state.grade)
    warnings = list(state.warnings) + [f"[compiler_node] 使用了默认输出: {error_msg}"]
    return {
        "runtime": default_plan.model_dump(),
        "error_count": state.error_count + 1,
        "warnings": warnings,
    }


# 注册节点到工作流
def create_compiler_node():
    """创建 compiler 节点函数"""
    return compiler_node
