"""
formatter_node - 最终输出整合节点

职责：整合所有节点的输出，生成最终的教学方案
- 不再调用 LLM，直接整合已有数据
- 确保输出格式一致
- 添加元数据和统计信息

输入：plan（骨架）+ knowledge（知识）+ design（互动）+ content（内容）
输出：FinalOutput: 强类型 Pydantic Model

重构说明：
- 使用 Pydantic FinalOutput 作为最终输出
- 所有数据通过 Pydantic Model 处理
- 保证类型安全和输出格式一致
"""

import datetime
from typing import Dict, Any
from utils.logger import get_logger
from graph.state import TeachingState
from models.planner import TeachingObjectives, TeachingStage
from models.knowledge import KnowledgeOutput
from models.design import InteractionDesign, QuestionStrategy, EngagementPattern, FeedbackMechanism
from models.content import PracticeDesign, BlackboardDesign, HomeworkItem, ContentMistake, TeacherScript
from models.final import FinalOutput, PlanMetadata, OutputStatistics

logger = get_logger(__name__)


def formatter_node(state: TeachingState) -> Dict[str, Any]:
    """
    最终输出整合节点

    直接整合所有节点的输出，不再调用 LLM。
    使用 Pydantic Model 确保类型安全。

    返回 partial update: {"final_output": FinalOutput}
    """
    topic = state.topic
    grade = state.grade
    plan = state.plan
    knowledge = state.knowledge
    design = state.design
    content = state.content

    logger.info(f"开始整合最终教学方案: 主题={topic}, 年级={grade}")

    try:
        # 整合所有节点的输出
        final_output = _integrate_outputs(topic, grade, plan, knowledge, design, content)

        logger.info("成功整合最终教学方案")
        # 返回 partial update
        return {"final_output": final_output.model_dump()}

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
) -> FinalOutput:
    """
    整合所有节点的输出

    使用 Pydantic Model 进行类型安全的数据处理
    """
    # 元数据
    metadata = PlanMetadata(
        topic=topic,
        grade=grade,
        generated_at=datetime.datetime.now().isoformat(),
        version="2.0",
        total_duration=plan.get("lesson_duration", "45分钟")
    )

    # 课程概述
    lesson_overview = plan.get("lesson_overview", "")

    # 教学目标
    teaching_objectives = None
    if "teaching_objectives" in plan:
        try:
            teaching_objectives = TeachingObjectives(**plan["teaching_objectives"])
        except Exception:
            pass

    # 教学流程
    teaching_process = []
    for stage in plan.get("teaching_process", []):
        try:
            teaching_process.append(TeachingStage(**stage))
        except Exception:
            pass

    # 互动设计
    interaction_design = []
    for item in design.get("interaction_design", []):
        try:
            interaction_design.append(InteractionDesign(**item))
        except Exception:
            pass

    # 提问策略
    question_strategy = None
    if "question_strategy" in design:
        try:
            question_strategy = QuestionStrategy(**design["question_strategy"])
        except Exception:
            pass

    # 参与模式
    engagement_patterns = []
    for item in design.get("engagement_patterns", []):
        try:
            engagement_patterns.append(EngagementPattern(**item))
        except Exception:
            pass

    # 反馈机制
    feedback_mechanisms = []
    for item in design.get("feedback_mechanisms", []):
        try:
            feedback_mechanisms.append(FeedbackMechanism(**item))
        except Exception:
            pass

    # 练习题设计
    practice_design = None
    if "practice_design" in content:
        try:
            practice_design = PracticeDesign(**content["practice_design"])
        except Exception:
            pass

    # 板书设计
    blackboard_design = None
    if "blackboard_design" in content:
        try:
            blackboard_design = BlackboardDesign(**content["blackboard_design"])
        except Exception:
            pass

    # 作业设计
    homework = []
    for item in content.get("homework", []):
        try:
            homework.append(HomeworkItem(**item))
        except Exception:
            pass

    # 易错点
    common_mistakes = []
    for item in content.get("common_mistakes", []):
        try:
            common_mistakes.append(ContentMistake(**item))
        except Exception:
            pass

    # 教师话术
    teacher_script = []
    for item in content.get("teacher_script", []):
        try:
            teacher_script.append(TeacherScript(**item))
        except Exception:
            pass

    # 知识结构
    knowledge_structure = None
    if knowledge:
        try:
            knowledge_structure = KnowledgeOutput(**knowledge)
        except Exception:
            pass

    # 统计信息
    statistics = _generate_statistics(
        practice_design=practice_design,
        interaction_design=interaction_design,
        homework=homework,
        common_mistakes=common_mistakes
    )

    # 构建最终输出
    return FinalOutput(
        metadata=metadata,
        lesson_overview=lesson_overview,
        teaching_objectives=teaching_objectives,
        teaching_process=teaching_process,
        interaction_design=interaction_design,
        question_strategy=question_strategy,
        engagement_patterns=engagement_patterns,
        feedback_mechanisms=feedback_mechanisms,
        practice_design=practice_design,
        blackboard_design=blackboard_design,
        homework=homework,
        common_mistakes=common_mistakes,
        teacher_script=teacher_script,
        knowledge_structure=knowledge_structure,
        statistics=statistics
    )


def _generate_statistics(
    practice_design: PracticeDesign = None,
    interaction_design: list = None,
    homework: list = None,
    common_mistakes: list = None
) -> OutputStatistics:
    """生成统计信息"""
    basic_count = len(practice_design.basic) if practice_design else 0
    intermediate_count = len(practice_design.intermediate) if practice_design else 0
    advanced_count = len(practice_design.advanced) if practice_design else 0
    total_questions = basic_count + intermediate_count + advanced_count

    interactive_count = len(interaction_design) if interaction_design else 0
    homework_count = len(homework) if homework else 0
    mistakes_count = len(common_mistakes) if common_mistakes else 0

    return OutputStatistics(
        total_questions=total_questions,
        basic_questions=basic_count,
        intermediate_questions=intermediate_count,
        advanced_questions=advanced_count,
        interactive_points=interactive_count,
        homework_count=homework_count,
        common_mistakes_count=mistakes_count
    )


def _handle_error(state: TeachingState, error_msg: str) -> Dict[str, Any]:
    """
    处理错误情况

    返回 partial update
    """
    logger.error(f"formatter_node 错误: {error_msg}")

    # 创建最小化的默认输出
    default_output = FinalOutput(
        metadata=PlanMetadata(
            topic=state.topic,
            grade=state.grade,
            generated_at=datetime.datetime.now().isoformat(),
            version="2.0",
            total_duration="未知"
        ),
        lesson_overview="教学方案生成失败，请重试",
        error=error_msg,
        statistics=OutputStatistics()
    )

    return {
        "final_output": default_output.model_dump(),
        "error_count": state.error_count + 1
    }


# 注册节点到工作流
def create_formatter_node():
    """创建 formatter 节点函数"""
    return formatter_node
