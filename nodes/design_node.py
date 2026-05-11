"""
design_node - 通用教学行为设计节点

核心理念：设计"通用教学行为"，与具体学科无关

职责：
- 设计教学行为模式（不涉及具体知识）
- 规划课堂互动逻辑
- 确定提问策略
- 设计反馈机制

输出：
- DesignOutput: 强类型 Pydantic Model

禁止生成：
- 具体学科知识（由 content_node 负责）
- 具体问题内容（由 content_node 负责）
- 具体案例（由 content_node 负责）

重构说明：
- 删除手写 _get_design_schema() JSON Schema dict
- 使用 Pydantic DesignOutput 作为结构化输出
- 使用 generate_structured_output_v2() 自动校验
"""

import json
from typing import Dict, Any, List
from pydantic import ValidationError
from utils.logger import get_logger
from graph.state import TeachingState
from llm.factory import get_llm_for_state
from models.design import DesignOutput, InteractionDesign

logger = get_logger(__name__)


# 互动类型（学科无关）
INTERACTION_TYPES = [
    "情境导入",
    "问题驱动",
    "探究学习",
    "类比教学",
    "小组合作",
    "案例分析",
    "任务驱动",
    "归纳总结",
    "实践操作",
    "反思评价"
]

# 教学方法（学科无关）
PEDAGOGY_METHODS = [
    "启发式教学",
    "探究式教学",
    "合作式教学",
    "任务式教学",
    "支架式教学",
    "范例式教学",
    "对比式教学"
]

# 认知层次（布鲁姆分类）
COGNITIVE_LEVELS = [
    "记忆",
    "理解",
    "应用",
    "分析",
    "评价",
    "创造"
]


def validate_design_output(output: DesignOutput) -> List[str]:
    """
    验证 DesignOutput 的业务规则

    Pydantic 已经保证了类型安全，
    这里只做业务层面的验证。

    返回: 问题列表（空表示通过）
    """
    issues = []

    # 检查 interaction_design 数量
    if len(output.interaction_design) < 2:
        issues.append(f"interaction_design 只有{len(output.interaction_design)}个互动点，要求至少2个")

    # 检查每个互动点
    for i, interaction in enumerate(output.interaction_design):
        # 检查是否包含具体学科内容
        _check_no_subject_content(interaction, f"interaction_design[{i}]", issues)

    # 检查 question_strategy
    if not output.question_strategy.approach:
        issues.append("question_strategy缺少approach")

    return issues


def _check_no_subject_content(data: Any, path: str, issues: List[str]) -> None:
    """检查是否包含具体学科内容"""
    if isinstance(data, str):
        subject_words = [
            "二次函数", "抛物线", "方程", "不等式",
            "OSI", "TCP", "IP", "以太网", "路由器",
            "光合作用", "细胞", "DNA",
            "牛顿", "加速度", "力",
            "元素周期表", "化学键"
        ]
        for word in subject_words:
            if word in data:
                issues.append(f"{path}包含具体学科内容: {word}")
                break
    elif isinstance(data, dict):
        for key, value in data.items():
            _check_no_subject_content(value, f"{path}.{key}", issues)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            _check_no_subject_content(item, f"{path}[{i}]", issues)


def _extract_cognitive_route(plan: Dict[str, Any]) -> str:
    """从 plan 中提取认知路线（不包含具体学科内容）"""
    cognitive_progression = plan.get("cognitive_progression", [])
    teaching_process = plan.get("teaching_process", [])

    route_parts = []

    if cognitive_progression:
        route_parts.append("认知递进路径:")
        for i, step in enumerate(cognitive_progression):
            route_parts.append(f"  {i+1}. {step}")

    if teaching_process:
        route_parts.append("\n认知阶段:")
        for stage in teaching_process:
            stage_name = stage.get("stage_name", "")
            strategy = stage.get("teaching_strategy", "")
            route_parts.append(f"  - {stage_name} (策略: {strategy})")

    return "\n".join(route_parts) if route_parts else "认知路线待设计"


def create_default_design_output() -> DesignOutput:
    """创建默认的通用教学行为"""
    from models.design import (
        TeacherBehavior, StudentBehavior, QuestionStrategy,
        EngagementPattern, FeedbackMechanism
    )

    return DesignOutput(
        interaction_design=[
            InteractionDesign(
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
                transition_to_next="引导学生进入探究阶段"
            ),
            InteractionDesign(
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
                transition_to_next="进入模型建构阶段"
            )
        ],
        question_strategy=QuestionStrategy(
            approach="递进式提问",
            progression="从具体到抽象，从简单到复杂",
            techniques=["开放性问题激发思考", "追问引导深入", "反问引发反思"]
        ),
        engagement_patterns=[
            EngagementPattern(
                pattern_name="小组讨论",
                when_to_use="需要学生合作探究时",
                how_to_implement="分组讨论，每组汇报",
                expected_effect="提高参与度，促进思维碰撞"
            )
        ],
        feedback_mechanisms=[
            FeedbackMechanism(
                type="正向反馈",
                trigger="学生回答正确",
                response="肯定并追问深化",
                purpose="强化正确理解"
            ),
            FeedbackMechanism(
                type="引导性反馈",
                trigger="学生回答不完整",
                response="提供提示，引导补充",
                purpose="帮助学生完善思考"
            )
        ]
    )


def design_node(state: TeachingState) -> Dict[str, Any]:
    """
    通用教学行为设计节点

    使用 Pydantic Model 作为结构化输出，
    自动校验类型和必填字段。

    返回 partial update: {"design": DesignOutput}
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

    # 构建 Prompt - 只传递认知路线，不传递具体主题
    cognitive_route = _extract_cognitive_route(plan)
    prompt = prompt_template.replace('{cognitive_route}', cognitive_route)

    try:
        # 调用 LLM API，使用 Pydantic Model 自动校验
        llm_client = get_llm_for_state(state.model_dump())

        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 使用新的 v2 接口，自动从 DesignOutput 生成 schema
                design_output = llm_client.generate_structured_output_v2(
                    prompt=prompt,
                    output_model=DesignOutput,
                    system_prompt=_get_system_prompt()
                )

                # 业务层面验证
                issues = validate_design_output(design_output)

                if not issues:
                    logger.info("成功设计通用教学行为")
                    # 返回 partial update
                    return {"design": design_output.model_dump()}
                else:
                    logger.warning(f"输出验证未通过 (尝试 {attempt + 1}/{max_retries}):")
                    for issue in issues:
                        logger.warning(f"  - {issue}")

                    # 如果是最后一次尝试，使用当前结果
                    if attempt == max_retries - 1:
                        logger.warning("达到最大重试次数，使用当前结果")
                        return {"design": design_output.model_dump()}

            except ValidationError as e:
                # Pydantic 验证失败
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
    """
    处理错误情况

    返回 partial update
    """
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
