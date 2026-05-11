"""
design_node - 通用教学行为设计节点

核心理念：设计"通用教学行为"，与具体学科无关

职责：
- 设计教学行为模式（不涉及具体知识）
- 规划课堂互动逻辑
- 确定提问策略

输出：
- InteractionDesign: 强类型 Pydantic Model (Cognitive IR)

禁止生成：
- 具体学科知识（由 content_node 负责）
- 具体问题内容（由 content_node 负责）
- 具体案例（由 content_node 负责）
"""

import json
from typing import Dict, Any, List
from pydantic import ValidationError
from utils.logger import get_logger
from graph.state import TeachingState
from llm.factory import get_llm_for_state
from models.cognitive import InteractionDesign, InteractionPoint, QuestionStrategy

logger = get_logger(__name__)


# 互动类型（学科无关）
INTERACTION_TYPES = [
    "情境导入", "问题驱动", "探究学习", "类比教学",
    "小组合作", "案例分析", "任务驱动", "归纳总结",
    "实践操作", "反思评价"
]

# 教学方法（学科无关）
PEDAGOGY_METHODS = [
    "启发式教学", "探究式教学", "合作式教学", "任务式教学",
    "支架式教学", "范例式教学", "对比式教学"
]


def validate_design_output(output: InteractionDesign) -> List[str]:
    """验证 InteractionDesign 的业务规则"""
    issues = []

    if len(output.interaction_points) < 2:
        issues.append(f"interaction_points 只有{len(output.interaction_points)}个互动点，要求至少2个")

    if not output.question_strategy.approach:
        issues.append("question_strategy缺少approach")

    return issues


def _extract_cognitive_route(plan: Dict[str, Any]) -> str:
    """从 plan (CognitiveFlow dict) 中提取认知路线"""
    cognitive_progression = plan.get("cognitive_progression", [])
    stages = plan.get("stages", [])

    route_parts = []

    if cognitive_progression:
        route_parts.append("认知递进路径:")
        for i, step in enumerate(cognitive_progression):
            route_parts.append(f"  {i+1}. {step}")

    if stages:
        route_parts.append("\n认知阶段:")
        for stage in stages:
            stage_name = stage.get("stage_name", "")
            strategy = stage.get("teaching_strategy", "")
            route_parts.append(f"  - {stage_name} (策略: {strategy})")

    return "\n".join(route_parts) if route_parts else "认知路线待设计"


def create_default_design_output() -> InteractionDesign:
    """创建默认的通用教学行为"""
    from models.cognitive import TeacherBehavior, StudentBehavior

    return InteractionDesign(
        interaction_points=[
            InteractionPoint(
                stage_name="认知冲突阶段",
                interaction_type="问题驱动",
                pedagogy_method="启发式教学",
                teacher_behavior=TeacherBehavior(
                    action="提出开放性问题，等待学生思考",
                    purpose="激发认知冲突",
                    duration="5分钟"
                ),
                student_behavior=StudentBehavior(
                    action="独立思考，尝试回答",
                    cognitive_activity="分析问题，调用已有知识",
                    expected_outcome="产生认知冲突"
                ),
                interaction_goal="激发学习兴趣",
                cognitive_level="分析",
                scaffolding_strategy="提供思考方向提示",
            ),
            InteractionPoint(
                stage_name="规律发现阶段",
                interaction_type="探究学习",
                pedagogy_method="探究式教学",
                teacher_behavior=TeacherBehavior(
                    action="展示多个案例，引导观察",
                    purpose="帮助学生发现规律",
                    duration="10分钟"
                ),
                student_behavior=StudentBehavior(
                    action="小组讨论，尝试归纳",
                    cognitive_activity="观察、比较、归纳",
                    expected_outcome="发现规律"
                ),
                interaction_goal="引导学生自主发现",
                cognitive_level="分析",
                scaffolding_strategy="提供对比框架",
            )
        ],
        question_strategy=QuestionStrategy(
            approach="递进式提问",
            progression="从具体到抽象，从简单到复杂",
            techniques=["开放性问题激发思考", "追问引导深入", "反问引发反思"]
        ),
    )


def design_node(state: TeachingState) -> Dict[str, Any]:
    """
    通用教学行为设计节点

    使用 Pydantic Model 作为结构化输出，
    自动校验类型和必填字段。

    返回 partial update: {"design": InteractionDesign}
    """
    topic = state.topic
    grade = state.grade
    plan = state.plan

    logger.info(f"开始设计通用教学行为: 主题={topic}, 年级={grade}")

    # 读取 Prompt 模板
    try:
        with open("prompts/interaction.txt", "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logger.error("未找到 interaction.txt prompt 文件")
        return _handle_error(state, "Prompt file not found")

    # 构建 Prompt
    cognitive_route = _extract_cognitive_route(plan)
    prompt = prompt_template.replace('{cognitive_route}', cognitive_route)

    try:
        # 调用 LLM API
        llm_client = get_llm_for_state(state.model_dump())

        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 使用 v2 接口，自动从 InteractionDesign 生成 schema
                design_output = llm_client.generate_structured_output_v2(
                    prompt=prompt,
                    output_model=InteractionDesign,
                    system_prompt=_get_system_prompt()
                )

                # 业务层面验证
                issues = validate_design_output(design_output)

                if not issues:
                    logger.info("成功设计通用教学行为")
                    return {"design": design_output.model_dump()}
                else:
                    logger.warning(f"输出验证未通过 (尝试 {attempt + 1}/{max_retries}):")
                    for issue in issues:
                        logger.warning(f"  - {issue}")

                    if attempt == max_retries - 1:
                        logger.warning("达到最大重试次数，使用当前结果")
                        return {"design": design_output.model_dump()}

            except ValidationError as e:
                logger.warning(f"Pydantic 验证失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.warning("达到最大重试次数，使用默认结果")
                    default_output = create_default_design_output()
                    return {"design": default_output.model_dump()}

            except Exception as e:
                logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
                if attempt == max_retries - 1:
                    raise

        # 如果所有尝试都失败，创建默认值
        logger.warning("所有重试都失败，使用默认教学行为")
        default_output = create_default_design_output()
        return {"design": default_output.model_dump()}

    except Exception as e:
        logger.error(f"design_node 执行失败: {e}")
        return _handle_error(state, str(e))


def _get_system_prompt() -> str:
    """获取系统提示"""
    return (
        "你是一位精通教学法的课堂互动设计师。\n"
        "你的任务是设计'通用教学行为'，与具体学科无关。\n\n"
        "【核心理念】\n"
        "1. 你设计的是'教学行为模式'，而不是'学科内容'\n"
        "2. 不要包含具体的学科知识（如数学公式、物理定律、历史事件等）\n"
        "3. 专注'如何教'，而不是'教什么'\n"
        "4. 具体的知识内容由后续 content_node 填充\n"
    )


def _handle_error(state: TeachingState, error_msg: str) -> Dict[str, Any]:
    """处理错误情况"""
    logger.error(f"design_node 错误: {error_msg}")

    default_output = create_default_design_output()
    return {
        "design": default_output.model_dump(),
        "error_count": state.error_count + 1
    }


# 注册节点到工作流
def create_design_node():
    """创建 design 节点函数"""
    return design_node
