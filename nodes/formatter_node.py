"""
formatter_node - 最终输出整合节点

重构后职责：
1. 整合所有节点的 Cognitive IR 输出
2. 使用 Renderer Pipeline 生成教师可读教案
3. 输出包含 Cognitive IR + TeacherLessonPlan

架构升级：
    Cognitive IR (planner + knowledge + design + content)
        ↓
    Renderer Pipeline (确定性转换，不调用 LLM)
        ↓
    TeacherLessonPlan (教师可读)
        ↓
    Markdown Renderer (格式化输出)

关键原则：
- Renderer 不调用 LLM
- Cognitive IR ≠ Teacher-facing Output
- 输出包含两层：AI 内部 + 教师可读
"""

import datetime
from typing import Dict, Any
from utils.logger import get_logger
from graph.state import TeachingState
from renderers.teacher_renderer import render_teacher_lesson_plan
from renderers.markdown_renderer import render_markdown

logger = get_logger(__name__)


def formatter_node(state: TeachingState) -> Dict[str, Any]:
    """
    最终输出整合节点

    使用 Renderer Pipeline 将 Cognitive IR 转换为教师可读教案。

    返回 partial update: {"final_output": {...}}
    """
    topic = state.topic
    grade = state.grade
    plan = state.plan
    knowledge = state.knowledge
    design = state.design
    content = state.content

    logger.info(f"开始整合最终教学方案: 主题={topic}, 年级={grade}")

    try:
        # 1. 使用 Renderer Pipeline 生成教师可读教案
        teacher_plan = render_teacher_lesson_plan(
            cognitive_flow=plan,
            knowledge_structure=knowledge,
            interaction_design=design,
            practice_design=content.get("practice_design"),
            misconception_model={"items": content.get("common_mistakes", [])},
            blackboard_design=content.get("blackboard_design"),
            homework=content.get("homework"),
            topic=topic,
            grade=grade,
        )

        # 3. 生成 Markdown 版本
        markdown_content = render_markdown(teacher_plan)

        # 4. 构建最终输出（包含两层）
        final_output = {
            # 元数据
            "metadata": {
                "topic": topic,
                "grade": grade,
                "generated_at": datetime.datetime.now().isoformat(),
                "version": "3.0",
                "total_duration": plan.get("lesson_duration", "45分钟"),
            },

            # 教师可读教案（主要输出）
            "teacher_lesson_plan": teacher_plan.model_dump(),

            # Markdown 版本（可直接阅读）
            "markdown": markdown_content,

            # Cognitive IR（AI 内部，供参考）
            "cognitive_ir": {
                "cognitive_flow": plan,
                "knowledge_structure": knowledge,
                "interaction_design": design,
                "practice_design": content.get("practice_design"),
                "misconception_model": content.get("common_mistakes", []),
                "blackboard_design": content.get("blackboard_design"),
                "homework": content.get("homework"),
            },

            # 统计信息
            "statistics": _generate_statistics(content),
        }

        logger.info("成功整合最终教学方案")
        return {"final_output": final_output}

    except Exception as e:
        logger.error(f"formatter_node 执行失败: {e}")
        return _handle_error(state, str(e))


def _generate_statistics(content: Dict[str, Any]) -> Dict[str, Any]:
    """生成统计信息"""
    practice = content.get("practice_design", {})
    basic_count = len(practice.get("basic", []))
    intermediate_count = len(practice.get("intermediate", []))
    advanced_count = len(practice.get("advanced", []))
    total_questions = basic_count + intermediate_count + advanced_count

    homework_count = len(content.get("homework", []))
    mistakes_count = len(content.get("common_mistakes", []))

    return {
        "total_questions": total_questions,
        "basic_questions": basic_count,
        "intermediate_questions": intermediate_count,
        "advanced_questions": advanced_count,
        "homework_count": homework_count,
        "common_mistakes_count": mistakes_count,
    }


def _handle_error(state: TeachingState, error_msg: str) -> Dict[str, Any]:
    """处理错误情况"""
    logger.error(f"formatter_node 错误: {error_msg}")

    return {
        "final_output": {
            "metadata": {
                "topic": state.topic,
                "grade": state.grade,
                "generated_at": datetime.datetime.now().isoformat(),
                "version": "3.0",
                "error": error_msg,
            },
            "teacher_lesson_plan": None,
            "markdown": f"# 教案生成失败\n\n错误信息：{error_msg}",
            "cognitive_ir": {},
            "statistics": {},
        },
        "error_count": state.error_count + 1,
    }


# 注册节点到工作流
def create_formatter_node():
    """创建 formatter 节点函数"""
    return formatter_node
