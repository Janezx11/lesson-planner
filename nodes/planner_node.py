"""
planner_node - 教学认知路线设计节点

核心理念：设计"学生认知推进路线"，而不是"教学目录"

职责：
- 设计认知阶段（不是传统教学阶段）
- 规划认知推进路径
- 确定每个阶段的教学策略
- 预期认知变化

输出：
- CognitiveFlow: 强类型 Pydantic Model (Cognitive IR)

禁止生成：
- 完整师生对话（由 design_node 负责）
- 练习题、板书、作业（由 content_node 负责）
"""

from typing import Dict, Any, List
from pydantic import ValidationError
from utils.logger import get_logger
from graph.state import TeachingState
from llm.factory import get_llm_for_state
from models.cognitive import CognitiveFlow, CognitiveStage

logger = get_logger(__name__)


# 认知阶段类型（用于验证）
COGNITIVE_STAGE_TYPES = [
    "认知冲突",
    "猜想建立",
    "错误辨析",
    "规律发现",
    "模型建构",
    "迁移应用",
    "实践验证",
    "案例分析"
]

# 教学策略类型（用于验证）
TEACHING_STRATEGIES = [
    "认知冲突",
    "类比教学",
    "错误驱动",
    "案例分析",
    "小组探究",
    "任务驱动",
    "直观演示",
    "对比分析"
]


def validate_planner_output(output: CognitiveFlow) -> List[str]:
    """
    验证 CognitiveFlow 的业务规则

    Pydantic 已经保证了类型安全，
    这里只做业务层面的验证。

    返回: 问题列表（空表示通过）
    """
    issues = []

    # 检查 lesson_overview 长度
    if len(output.lesson_overview) < 30:
        issues.append(f"lesson_overview 太短({len(output.lesson_overview)}字)，要求30字以上")

    # 检查 cognitive_progression 数量
    if len(output.cognitive_progression) < 3:
        issues.append(f"cognitive_progression 只有{len(output.cognitive_progression)}个阶段，要求至少3个")

    # 检查 stages 数量
    if len(output.stages) < 2:
        issues.append(f"stages 只有{len(output.stages)}个阶段，要求至少2个")

    # 检查每个阶段的认知化程度
    for i, stage in enumerate(output.stages):
        # 检查 stage_name 是否包含冒号（认知化格式）
        if ":" not in stage.stage_name and "：" not in stage.stage_name:
            issues.append(f"阶段{i+1}的stage_name不符合'认知状态：认知目标'格式: {stage.stage_name}")

        # 检查是否包含传统阶段名称
        traditional_names = ["情境导入", "新课讲解", "课堂练习", "总结提升", "导入", "讲解", "练习", "总结"]
        for trad_name in traditional_names:
            if trad_name in stage.stage_name:
                issues.append(f"阶段{i+1}的stage_name包含传统阶段名称: {trad_name}")
                break

        # 检查 teaching_strategy
        if not stage.teaching_strategy:
            issues.append(f"阶段'{stage.stage_name}'缺少teaching_strategy")

        # 检查 teacher_activity 是否具体
        for activity in stage.teacher_activity:
            abstract_words = ["讲解", "介绍", "引导学生理解", "说明", "阐述"]
            for word in abstract_words:
                if word in activity and len(activity) < 15:
                    issues.append(f"阶段'{stage.stage_name}'的teacher_activity过于抽象: {activity}")
                    break

    return issues


def create_default_planner_output() -> CognitiveFlow:
    """创建默认的认知推进路线（错误时使用）"""
    return CognitiveFlow(
        lesson_overview="认知路线设计失败，请重试",
        lesson_duration="45分钟",
        cognitive_progression=[
            "学生初始状态：对主题有初步了解",
            "阶段1后：产生认知冲突",
            "阶段2后：理解核心概念",
            "最终状态：能够应用所学知识"
        ],
        stages=[
            CognitiveStage(
                stage_name="认知冲突：为什么需要学习这个",
                cognitive_state="学生对主题有初步认识，但缺乏深入理解",
                cognitive_goal="激发学习兴趣，建立认知冲突",
                teaching_strategy="认知冲突",
                duration="8分钟",
                teacher_activity=["展示与主题相关的真实案例", "提出引发思考的问题"],
                student_activity=["观察案例，产生疑问", "尝试回答问题"],
                expected_cognitive_change="从'认为简单'到'意识到复杂'"
            ),
            CognitiveStage(
                stage_name="规律发现：从现象中找规律",
                cognitive_state="学生产生了认知冲突，想要寻找答案",
                cognitive_goal="引导学生发现规律",
                teaching_strategy="案例分析",
                duration="15分钟",
                teacher_activity=["展示多个相关案例", "引导学生对比分析"],
                student_activity=["分析案例，寻找共同点", "尝试总结规律"],
                expected_cognitive_change="从'困惑'到'初步理解'"
            ),
            CognitiveStage(
                stage_name="模型建构：建立抽象模型",
                cognitive_state="学生发现了规律，需要建立系统认知",
                cognitive_goal="帮助学生建立抽象模型",
                teaching_strategy="直观演示",
                duration="12分钟",
                teacher_activity=["用图示展示抽象模型", "用类比帮助理解"],
                student_activity=["理解模型", "用自己的话解释"],
                expected_cognitive_change="从'具体理解'到'抽象认知'"
            )
        ]
    )


def planner_node(state: TeachingState) -> Dict[str, Any]:
    """
    教学认知路线设计节点

    使用 Pydantic Model 作为结构化输出，
    自动校验类型和必填字段。

    返回 partial update: {"plan": CognitiveFlow}
    """
    topic = state.topic
    grade = state.grade

    logger.info(f"开始设计认知推进路线: 主题={topic}, 年级={grade}")

    # 读取 Prompt 模板
    try:
        with open("prompts/planner.txt", "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logger.error("未找到 planner.txt prompt 文件")
        return _handle_error(state, "Prompt file not found")

    # 构建 Prompt
    prompt = prompt_template.replace('{topic}', topic).replace('{grade}', grade)

    try:
        # 调用 LLM API，使用 Pydantic Model 自动校验
        llm_state = {**state.model_dump(), 'temperature': 0.3}
        llm_client = get_llm_for_state(llm_state)

        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 使用 v2 接口，自动从 CognitiveFlow 生成 schema
                planner_output = llm_client.generate_structured_output_v2(
                    prompt=prompt,
                    output_model=CognitiveFlow,
                    system_prompt=_get_system_prompt()
                )

                # 业务层面验证
                issues = validate_planner_output(planner_output)

                if not issues:
                    logger.info("成功设计认知推进路线")
                    # 返回 partial update，plan 是 CognitiveFlow 实例
                    return {"plan": planner_output.model_dump()}
                else:
                    logger.warning(f"输出验证未通过 (尝试 {attempt + 1}/{max_retries}):")
                    for issue in issues:
                        logger.warning(f"  - {issue}")

                    # 如果是最后一次尝试，使用当前结果
                    if attempt == max_retries - 1:
                        logger.warning("达到最大重试次数，使用当前结果")
                        return {"plan": planner_output.model_dump()}

            except ValidationError as e:
                # Pydantic 验证失败
                logger.warning(f"Pydantic 验证失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.warning("达到最大重试次数，使用默认结果")
                    default_output = create_default_planner_output()
                    return {"plan": default_output.model_dump()}

            except Exception as e:
                logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
                if attempt == max_retries - 1:
                    raise

        # 如果所有尝试都失败，创建默认值
        logger.warning("所有重试都失败，使用默认认知路线")
        default_output = create_default_planner_output()
        return {"plan": default_output.model_dump()}

    except Exception as e:
        logger.error(f"planner_node 执行失败: {e}")
        return _handle_error(state, str(e))


def _get_system_prompt() -> str:
    """获取系统提示"""
    return (
        "你是一位深谙认知科学的教学设计师。\n"
        "你的任务是设计学生认知推进路线，而不是传统教学目录。\n\n"
        "【核心理念】\n"
        "1. 不要使用'情境导入→新课讲解→课堂练习→总结提升'这种传统阶段\n"
        "2. 根据主题动态生成认知阶段：认知冲突、猜想建立、错误辨析、规律发现、模型建构、迁移应用等\n"
        "3. stage_name 必须是'认知状态：认知目标'格式，如'认知冲突：为什么网络通信不能乱来'\n"
        "4. teacher_activity 必须是具体可视化动作，不要写'讲解XXX'这种抽象描述\n"
        "5. 必须包含 cognitive_progression 字段，描述学生认知如何一步步推进\n"
        "6. 必须包含 teaching_strategy 字段，说明本阶段采用的教学策略\n"
    )


def _handle_error(state: TeachingState, error_msg: str) -> Dict[str, Any]:
    """
    处理错误情况

    返回 partial update
    """
    logger.error(f"planner_node 错误: {error_msg}")

    default_output = create_default_planner_output()
    return {
        "plan": default_output.model_dump(),
        "error_count": state.error_count + 1
    }


# 注册节点到工作流
def create_planner_node():
    """创建 planner 节点函数"""
    return planner_node
