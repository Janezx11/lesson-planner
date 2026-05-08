"""
planner_node - 教学认知路线设计节点

核心理念：设计"学生认知推进路线"，而不是"教学目录"

职责：
- 设计认知阶段（不是传统教学阶段）
- 规划认知推进路径
- 确定每个阶段的教学策略
- 预期认知变化

输出：
- lesson_overview: 认知主线
- cognitive_progression: 认知递进路径
- teaching_process: 认知阶段设计

禁止生成：
- 完整师生对话（由 design_node 负责）
- 练习题、板书、作业（由 content_node 负责）
"""

from typing import Dict, Any, List
from utils.logger import get_logger
from graph.state import TeachingState
from llm.factory import get_llm_for_state

logger = get_logger(__name__)


# planner_node 必须生成的字段
PLANNER_REQUIRED_FIELDS = [
    "lesson_overview",
    "cognitive_progression",
    "teaching_process"
]

# 认知阶段类型
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

# 教学策略类型
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


def normalize_planner_output(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    标准化 planner_node 输出

    确保输出符合认知推进架构
    """
    result = {}

    # 课程概述（认知主线）
    result["lesson_overview"] = raw_data.get("lesson_overview", "")

    # 课时时长
    result["lesson_duration"] = raw_data.get("lesson_duration", "45分钟")

    # 学情分析（可选）
    if "student_analysis" in raw_data:
        result["student_analysis"] = raw_data["student_analysis"]

    # 教学目标（可选）
    if "teaching_objectives" in raw_data:
        result["teaching_objectives"] = raw_data["teaching_objectives"]

    # 认知递进路径
    result["cognitive_progression"] = raw_data.get("cognitive_progression", [])

    # 教学过程（认知阶段）
    teaching_process = raw_data.get("teaching_process", [])
    normalized_process = []

    for stage in teaching_process:
        normalized_stage = {
            "stage_name": stage.get("stage_name", ""),
            "cognitive_state": stage.get("cognitive_state", ""),
            "cognitive_goal": stage.get("cognitive_goal", ""),
            "teaching_strategy": stage.get("teaching_strategy", ""),
            "duration": stage.get("duration", ""),
            "teacher_activity": _ensure_list(stage.get("teacher_activity", [])),
            "student_activity": _ensure_list(stage.get("student_activity", [])),
            "expected_cognitive_change": stage.get("expected_cognitive_change", "")
        }
        normalized_process.append(normalized_stage)

    result["teaching_process"] = normalized_process

    # 删除不应由 planner 生成的字段
    fields_to_remove = [
        "practice_design", "common_mistakes", "blackboard_design",
        "homework", "teaching_tips", "key_questions", "steps",
        "teacher_followup", "expected_student_response", "scaffolding",
        "interactive_design", "question_chain"
    ]
    for field in fields_to_remove:
        if field in result:
            del result[field]

    return result


def _ensure_list(value) -> List[str]:
    """确保值是列表格式"""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value] if value else []
    return []


def validate_planner_output(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    验证 planner_node 输出

    返回: (是否通过, 问题列表)
    """
    issues = []

    # 检查必需字段
    for field in PLANNER_REQUIRED_FIELDS:
        if field not in data:
            issues.append(f"缺少必需字段: {field}")

    # 检查 lesson_overview
    overview = data.get("lesson_overview", "")
    if len(overview) < 30:
        issues.append(f"lesson_overview 太短({len(overview)}字)，要求30字以上")

    # 检查 cognitive_progression
    progression = data.get("cognitive_progression", [])
    if len(progression) < 3:
        issues.append(f"cognitive_progression 只有{len(progression)}个阶段，要求至少3个")

    # 检查 teaching_process
    teaching_process = data.get("teaching_process", [])
    if len(teaching_process) < 2:
        issues.append(f"teaching_process 只有{len(teaching_process)}个阶段，要求至少2个")

    # 检查每个阶段的认知化程度
    for i, stage in enumerate(teaching_process):
        stage_name = stage.get("stage_name", "")

        # 检查 stage_name 是否包含冒号（认知化格式）
        if ":" not in stage_name and "：" not in stage_name:
            issues.append(f"阶段{i+1}的stage_name不符合'认知状态：认知目标'格式: {stage_name}")

        # 检查是否包含传统阶段名称
        traditional_names = ["情境导入", "新课讲解", "课堂练习", "总结提升", "导入", "讲解", "练习", "总结"]
        for trad_name in traditional_names:
            if trad_name in stage_name:
                issues.append(f"阶段{i+1}的stage_name包含传统阶段名称: {trad_name}")
                break

        # 检查 teaching_strategy
        strategy = stage.get("teaching_strategy", "")
        if not strategy:
            issues.append(f"阶段'{stage_name}'缺少teaching_strategy")

        # 检查 teacher_activity 是否具体
        activities = stage.get("teacher_activity", [])
        for activity in activities:
            # 检查是否包含抽象词汇
            abstract_words = ["讲解", "介绍", "引导学生理解", "说明", "阐述"]
            for word in abstract_words:
                if word in activity and len(activity) < 15:
                    issues.append(f"阶段'{stage_name}'的teacher_activity过于抽象: {activity}")
                    break

    # 检查 JSON 大小
    import json
    json_str = json.dumps(data, ensure_ascii=False)
    token_estimate = len(json_str) // 2
    if token_estimate > 2500:
        issues.append(f"JSON过大(约{token_estimate}tokens)，要求小于2500tokens")

    return len(issues) == 0, issues


def planner_node(state: TeachingState) -> TeachingState:
    """
    教学认知路线设计节点

    设计学生认知推进路线，而不是传统教学目录
    """
    topic = state["topic"]
    grade = state["grade"]

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

    # 定义 Schema
    expected_schema = _get_planner_schema()

    try:
        # 临时设置低 temperature
        llm_state = {**state, 'temperature': 0.3}

        # 调用 LLM API
        llm_client = get_llm_for_state(llm_state)

        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                raw_data = llm_client.generate_structured_output(
                    prompt=prompt,
                    schema=expected_schema,
                    system_prompt=_get_system_prompt(),
                    required_fields=PLANNER_REQUIRED_FIELDS
                )

                # 标准化输出
                plan_data = normalize_planner_output(raw_data)

                # 验证输出
                is_valid, issues = validate_planner_output(plan_data)

                if is_valid:
                    logger.info("成功设计认知推进路线")
                    return {
                        **state,
                        "plan": plan_data
                    }
                else:
                    logger.warning(f"输出验证未通过 (尝试 {attempt + 1}/{max_retries}):")
                    for issue in issues:
                        logger.warning(f"  - {issue}")

                    # 如果是最后一次尝试，使用当前结果
                    if attempt == max_retries - 1:
                        logger.warning("达到最大重试次数，使用当前结果")
                        return {
                            **state,
                            "plan": plan_data
                        }

            except Exception as e:
                logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
                if attempt == max_retries - 1:
                    raise

        # 如果所有尝试都失败，创建默认值
        logger.warning("所有重试都失败，使用默认认知路线")
        plan_data = _create_default_plan()
        return {
            **state,
            "plan": plan_data
        }

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
        "6. 必须包含 teaching_strategy 字段，说明本阶段采用的教学策略\n\n"
        "【输出格式】\n"
        "必须严格按照 JSON 格式输出，包含以下字段：\n"
        "- lesson_overview: 认知主线（100字以内）\n"
        "- cognitive_progression: 认知递进路径数组\n"
        "- teaching_process: 认知阶段数组\n"
    )


def _get_planner_schema() -> Dict[str, Any]:
    """获取 planner_node 的 JSON Schema"""
    return {
        "type": "object",
        "properties": {
            "lesson_overview": {"type": "string"},
            "lesson_duration": {"type": "string"},
            "student_analysis": {
                "type": "object",
                "properties": {
                    "level": {"type": "string"},
                    "characteristics": {"type": "string"}
                }
            },
            "teaching_objectives": {
                "type": "object",
                "properties": {
                    "cognitive": {"type": "array", "items": {"type": "string"}},
                    "skill": {"type": "array", "items": {"type": "string"}},
                    "attitude": {"type": "array", "items": {"type": "string"}}
                }
            },
            "cognitive_progression": {
                "type": "array",
                "items": {"type": "string"}
            },
            "teaching_process": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "stage_name": {"type": "string"},
                        "cognitive_state": {"type": "string"},
                        "cognitive_goal": {"type": "string"},
                        "teaching_strategy": {"type": "string"},
                        "duration": {"type": "string"},
                        "teacher_activity": {"type": "array", "items": {"type": "string"}},
                        "student_activity": {"type": "array", "items": {"type": "string"}},
                        "expected_cognitive_change": {"type": "string"}
                    },
                    "required": ["stage_name", "teaching_strategy", "teacher_activity"]
                }
            }
        },
        "required": PLANNER_REQUIRED_FIELDS
    }


def _create_default_plan() -> Dict[str, Any]:
    """创建默认的认知推进路线"""
    return {
        "lesson_overview": "认知路线设计失败，请重试",
        "lesson_duration": "45分钟",
        "cognitive_progression": [
            "学生初始状态：对主题有初步了解",
            "阶段1后：产生认知冲突",
            "阶段2后：理解核心概念",
            "最终状态：能够应用所学知识"
        ],
        "teaching_process": [
            {
                "stage_name": "认知冲突：为什么需要学习这个",
                "cognitive_state": "学生对主题有初步认识，但缺乏深入理解",
                "cognitive_goal": "激发学习兴趣，建立认知冲突",
                "teaching_strategy": "认知冲突",
                "duration": "8分钟",
                "teacher_activity": [
                    "展示与主题相关的真实案例",
                    "提出引发思考的问题"
                ],
                "student_activity": [
                    "观察案例，产生疑问",
                    "尝试回答问题"
                ],
                "expected_cognitive_change": "从'认为简单'到'意识到复杂'"
            },
            {
                "stage_name": "规律发现：从现象中找规律",
                "cognitive_state": "学生产生了认知冲突，想要寻找答案",
                "cognitive_goal": "引导学生发现规律",
                "teaching_strategy": "案例分析",
                "duration": "15分钟",
                "teacher_activity": [
                    "展示多个相关案例",
                    "引导学生对比分析"
                ],
                "student_activity": [
                    "分析案例，寻找共同点",
                    "尝试总结规律"
                ],
                "expected_cognitive_change": "从'困惑'到'初步理解'"
            },
            {
                "stage_name": "模型建构：建立抽象模型",
                "cognitive_state": "学生发现了规律，需要建立系统认知",
                "cognitive_goal": "帮助学生建立抽象模型",
                "teaching_strategy": "直观演示",
                "duration": "12分钟",
                "teacher_activity": [
                    "用图示展示抽象模型",
                    "用类比帮助理解"
                ],
                "student_activity": [
                    "理解模型",
                    "用自己的话解释"
                ],
                "expected_cognitive_change": "从'具体理解'到'抽象认知'"
            }
        ]
    }


def _handle_error(state: TeachingState, error_msg: str) -> TeachingState:
    """处理错误情况"""
    logger.error(f"planner_node 错误: {error_msg}")

    default_plan = _create_default_plan()
    default_plan["error"] = error_msg

    new_state = {
        **state,
        "plan": default_plan,
        "error_count": state["error_count"] + 1
    }

    if new_state["error_count"] >= state["max_retries"]:
        logger.critical("达到最大重试次数，工作流将终止")

    return new_state


# 注册节点到工作流
def create_planner_node():
    """创建 planner 节点函数"""
    return planner_node
