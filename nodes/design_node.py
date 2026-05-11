"""
design_node - 通用教学行为设计节点

核心理念：设计"通用教学行为"，与具体学科无关

职责：
- 设计教学行为模式（不涉及具体知识）
- 规划课堂互动逻辑
- 确定提问策略
- 设计反馈机制

输出：
- interaction_design: 互动设计
- question_strategy: 提问策略
- engagement_patterns: 参与模式
- feedback_mechanisms: 反馈机制

禁止生成：
- 具体学科知识（由 content_node 负责）
- 具体问题内容（由 content_node 负责）
- 具体案例（由 content_node 负责）

重构说明：
- 改为返回 partial update（只返回 design 字段）
- 不再返回完整 state
- 由 workflow/builder 层负责 state merge
"""

import json
from typing import Dict, Any, List
from utils.logger import get_logger
from graph.state import TeachingState
from llm.factory import get_llm_for_state

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


def normalize_design_output(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    标准化 design_node 输出

    确保输出符合通用教学行为层
    """
    result = {}

    # 互动设计
    result["interaction_design"] = raw_data.get("interaction_design", [])

    # 提问策略
    result["question_strategy"] = raw_data.get("question_strategy", {
        "approach": "",
        "progression": "",
        "techniques": []
    })

    # 参与模式
    result["engagement_patterns"] = raw_data.get("engagement_patterns", [])

    # 反馈机制
    result["feedback_mechanisms"] = raw_data.get("feedback_mechanisms", [])

    return result


def validate_design_output(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    验证 design_node 输出

    返回: (是否通过, 问题列表)
    """
    issues = []

    # 检查 interaction_design
    interaction_design = data.get("interaction_design", [])
    if len(interaction_design) < 2:
        issues.append(f"interaction_design 只有{len(interaction_design)}个互动点，要求至少2个")

    # 检查每个互动点的结构
    for i, interaction in enumerate(interaction_design):
        # 检查是否包含具体学科内容
        _check_no_subject_content(interaction, f"interaction_design[{i}]", issues)

        # 检查必需字段
        if not interaction.get("interaction_type"):
            issues.append(f"互动点{i+1}缺少interaction_type")
        if not interaction.get("pedagogy_method"):
            issues.append(f"互动点{i+1}缺少pedagogy_method")
        if not interaction.get("teacher_behavior"):
            issues.append(f"互动点{i+1}缺少teacher_behavior")
        if not interaction.get("student_behavior"):
            issues.append(f"互动点{i+1}缺少student_behavior")

    # 检查 question_strategy
    question_strategy = data.get("question_strategy", {})
    if not question_strategy.get("approach"):
        issues.append("question_strategy缺少approach")

    # 检查 JSON 大小
    import json
    json_str = json.dumps(data, ensure_ascii=False)
    token_estimate = len(json_str) // 2
    if token_estimate > 2500:
        issues.append(f"JSON过大(约{token_estimate}tokens)，要求小于2500tokens")

    return len(issues) == 0, issues


def _check_no_subject_content(data: Any, path: str, issues: List[str]) -> None:
    """
    检查是否包含具体学科内容
    """
    if isinstance(data, str):
        # 检查是否包含具体学科词汇
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


def design_node(state: TeachingState) -> Dict[str, Any]:
    """
    通用教学行为设计节点

    设计与学科无关的教学行为模式

    重构后返回 partial update:
    - 成功时: {"design": design_data}
    - 失败时: {"design": default_design, "error_count": state.error_count + 1}
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

    # 定义 Schema
    expected_schema = _get_design_schema()

    try:
        # 调用 LLM API
        llm_client = get_llm_for_state(state.model_dump())

        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                raw_data = llm_client.generate_structured_output(
                    prompt=prompt,
                    schema=expected_schema,
                    system_prompt=_get_system_prompt(),
                    required_fields=["interaction_design"]
                )

                # 标准化输出
                design_data = normalize_design_output(raw_data)

                # 验证输出
                is_valid, issues = validate_design_output(design_data)

                if is_valid:
                    logger.info("成功设计通用教学行为")
                    # 返回 partial update，只包含 design 字段
                    return {"design": design_data}
                else:
                    logger.warning(f"输出验证未通过 (尝试 {attempt + 1}/{max_retries}):")
                    for issue in issues:
                        logger.warning(f"  - {issue}")

                    # 如果是最后一次尝试，使用当前结果
                    if attempt == max_retries - 1:
                        logger.warning("达到最大重试次数，使用当前结果")
                        return {"design": design_data}

            except Exception as e:
                logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
                if attempt == max_retries - 1:
                    raise

        # 如果所有尝试都失败，创建默认值
        logger.warning("所有重试都失败，使用默认教学行为")
        design_data = _create_default_design()
        return {"design": design_data}

    except Exception as e:
        logger.error(f"design_node 执行失败: {e}")
        return _handle_error(state, str(e))


def _extract_cognitive_route(plan: Dict[str, Any]) -> str:
    """
    从 plan 中提取认知路线（不包含具体学科内容）
    """
    cognitive_progression = plan.get("cognitive_progression", [])
    teaching_process = plan.get("teaching_process", [])

    # 构建认知路线描述
    route_parts = []

    # 认知递进路径
    if cognitive_progression:
        route_parts.append("认知递进路径:")
        for i, step in enumerate(cognitive_progression):
            route_parts.append(f"  {i+1}. {step}")

    # 认知阶段
    if teaching_process:
        route_parts.append("\n认知阶段:")
        for stage in teaching_process:
            stage_name = stage.get("stage_name", "")
            strategy = stage.get("teaching_strategy", "")
            route_parts.append(f"  - {stage_name} (策略: {strategy})")

    return "\n".join(route_parts) if route_parts else "认知路线待设计"


def _get_system_prompt() -> str:
    """获取系统提示"""
    return (
        "你是一位精通教学法的课堂互动设计师。\n"
        "你的任务是设计'通用教学行为'，与具体学科无关。\n\n"
        "【核心理念】\n"
        "1. 你设计的是'教学行为模式'，而不是'学科内容'\n"
        "2. 不要包含具体的学科知识（如数学公式、物理定律、历史事件等）\n"
        "3. 专注'如何教'，而不是'教什么'\n"
        "4. 具体的知识内容由后续 content_node 填充\n\n"
        "【输出格式】\n"
        "必须严格按照 JSON 格式输出，包含以下字段：\n"
        "- interaction_design: 互动设计数组\n"
        "- question_strategy: 提问策略\n"
        "- engagement_patterns: 参与模式\n"
        "- feedback_mechanisms: 反馈机制\n"
    )


def _get_design_schema() -> Dict[str, Any]:
    """获取 design_node 的 JSON Schema"""
    return {
        "type": "object",
        "properties": {
            "interaction_design": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "stage_name": {"type": "string"},
                        "interaction_type": {"type": "string"},
                        "pedagogy_method": {"type": "string"},
                        "teacher_behavior": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string"},
                                "purpose": {"type": "string"},
                                "duration": {"type": "string"}
                            },
                            "required": ["action", "purpose"]
                        },
                        "student_behavior": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string"},
                                "cognitive_activity": {"type": "string"},
                                "expected_outcome": {"type": "string"}
                            },
                            "required": ["action", "cognitive_activity"]
                        },
                        "interaction_goal": {"type": "string"},
                        "cognitive_level": {"type": "string"},
                        "scaffolding_strategy": {"type": "string"},
                        "transition_to_next": {"type": "string"}
                    },
                    "required": ["stage_name", "interaction_type", "teacher_behavior", "student_behavior"]
                }
            },
            "question_strategy": {
                "type": "object",
                "properties": {
                    "approach": {"type": "string"},
                    "progression": {"type": "string"},
                    "techniques": {"type": "array", "items": {"type": "string"}}
                }
            },
            "engagement_patterns": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "pattern_name": {"type": "string"},
                        "when_to_use": {"type": "string"},
                        "how_to_implement": {"type": "string"},
                        "expected_effect": {"type": "string"}
                    }
                }
            },
            "feedback_mechanisms": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "trigger": {"type": "string"},
                        "response": {"type": "string"},
                        "purpose": {"type": "string"}
                    }
                }
            }
        },
        "required": ["interaction_design"]
    }


def _create_default_design() -> Dict[str, Any]:
    """创建默认的通用教学行为"""
    return {
        "interaction_design": [
            {
                "stage_name": "认知冲突阶段",
                "interaction_type": "问题驱动",
                "pedagogy_method": "启发式教学",
                "teacher_behavior": {
                    "action": "提出开放性问题，等待学生思考",
                    "purpose": "激发认知冲突",
                    "duration": "5分钟"
                },
                "student_behavior": {
                    "action": "独立思考，尝试回答",
                    "cognitive_activity": "分析问题，调用已有知识",
                    "expected_outcome": "产生认知冲突"
                },
                "interaction_goal": "激发学习兴趣",
                "cognitive_level": "分析",
                "scaffolding_strategy": "提供思考方向提示",
                "transition_to_next": "引导学生进入探究阶段"
            },
            {
                "stage_name": "规律发现阶段",
                "interaction_type": "探究学习",
                "pedagogy_method": "探究式教学",
                "teacher_behavior": {
                    "action": "展示多个案例，引导观察",
                    "purpose": "帮助学生发现规律",
                    "duration": "10分钟"
                },
                "student_behavior": {
                    "action": "小组讨论，尝试归纳",
                    "cognitive_activity": "观察、比较、归纳",
                    "expected_outcome": "发现规律"
                },
                "interaction_goal": "引导学生自主发现",
                "cognitive_level": "分析",
                "scaffolding_strategy": "提供对比框架",
                "transition_to_next": "进入模型建构阶段"
            }
        ],
        "question_strategy": {
            "approach": "递进式提问",
            "progression": "从具体到抽象，从简单到复杂",
            "techniques": [
                "开放性问题激发思考",
                "追问引导深入",
                "反问引发反思"
            ]
        },
        "engagement_patterns": [
            {
                "pattern_name": "小组讨论",
                "when_to_use": "需要学生合作探究时",
                "how_to_implement": "分组讨论，每组汇报",
                "expected_effect": "提高参与度，促进思维碰撞"
            }
        ],
        "feedback_mechanisms": [
            {
                "type": "正向反馈",
                "trigger": "学生回答正确",
                "response": "肯定并追问深化",
                "purpose": "强化正确理解"
            },
            {
                "type": "引导性反馈",
                "trigger": "学生回答不完整",
                "response": "提供提示，引导补充",
                "purpose": "帮助学生完善思考"
            }
        ]
    }


def _handle_error(state: TeachingState, error_msg: str) -> Dict[str, Any]:
    """
    处理错误情况

    返回 partial update，包含默认 design 和递增的 error_count
    """
    logger.error(f"design_node 错误: {error_msg}")

    default_design = _create_default_design()
    default_design["error"] = error_msg

    # 返回 partial update，只包含 design 和 error_count
    return {
        "design": default_design,
        "error_count": state.error_count + 1
    }


# 注册节点到工作流
def create_design_node():
    """创建 design 节点函数"""
    return design_node
