"""
renderer_node - 渲染节点

职责：
- 读取 Teacher Runtime Plan
- 生成 Markdown 格式输出
- 构建最终输出结构

架构位置：
    TeacherRuntimePlan (由 compiler_node 生成)
        ↓
    renderer_node (确定性格式转换，不调用 LLM)
        ↓
    Markdown + final_output

关键原则：
- 不调用 LLM
- 不理解教学逻辑
- 只负责格式输出
"""

import datetime
from typing import Dict, Any
from utils.logger import get_logger
from graph.state import TeachingState
from models.runtime import TeacherRuntimePlan
from renderers.markdown_renderer import render_markdown

logger = get_logger(__name__)


def renderer_node(state: TeachingState) -> Dict[str, Any]:
    """
    渲染节点 — Teacher Runtime Plan → Markdown + final_output

    不调用 LLM，纯确定性格式转换。

    返回 partial update: {"final_output": {...}}
    """
    topic = state.topic
    grade = state.grade
    runtime = state.runtime

    logger.info(f"开始渲染最终输出: 主题={topic}, 年级={grade}")

    try:
        # 1. 解析 TeacherRuntimePlan
        runtime_plan = TeacherRuntimePlan.model_validate(runtime)

        # 2. 生成 Markdown
        markdown_content = render_markdown(runtime_plan)

        # 3. 构建最终输出
        final_output = {
            # 元数据
            "metadata": {
                "topic": topic,
                "grade": grade,
                "generated_at": datetime.datetime.now().isoformat(),
                "version": "4.0",
                "total_duration": runtime_plan.duration,
            },

            # 教师运行时教案（核心输出）
            "teacher_runtime_plan": runtime_plan.model_dump(),

            # Markdown 版本（可直接阅读）
            "markdown": markdown_content,

            # 统计信息
            "statistics": _generate_statistics(runtime_plan),
        }

        logger.info("成功渲染最终输出")
        return {"final_output": final_output}

    except Exception as e:
        logger.error(f"renderer_node 执行失败: {e}")
        return _handle_error(state, str(e))


def _generate_statistics(runtime_plan: TeacherRuntimePlan) -> Dict[str, Any]:
    """生成统计信息"""
    return {
        "total_sections": len(runtime_plan.sections),
        "total_interactions": len(runtime_plan.interactions),
        "total_questions": len(runtime_plan.practice_questions),
        "total_homework": len(runtime_plan.homework),
    }


def _handle_error(state: TeachingState, error_msg: str) -> Dict[str, Any]:
    """处理错误情况"""
    logger.error(f"renderer_node 错误: {error_msg}")

    return {
        "final_output": {
            "metadata": {
                "topic": state.topic,
                "grade": state.grade,
                "generated_at": datetime.datetime.now().isoformat(),
                "version": "4.0",
                "error": error_msg,
            },
            "teacher_runtime_plan": None,
            "markdown": f"# 教案生成失败\n\n错误信息：{error_msg}",
            "statistics": {},
        },
        "error_count": state.error_count + 1,
    }


# 注册节点到工作流
def create_renderer_node():
    """创建 renderer 节点函数"""
    return renderer_node
