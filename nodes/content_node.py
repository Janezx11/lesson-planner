"""
content_node - 教学内容生成节点

职责：根据教学计划骨架和互动设计，生成具体的教学内容
- practice_design: 练习题设计
- blackboard_design: 板书设计
- homework: 作业设计
- teacher_script: 教师话术
- common_mistakes: 易错点分析

输入：planner_node 输出（教学骨架）+ design_node 输出（互动设计）
输出：教学内容

重构说明：
- 改为返回 partial update（只返回 content 字段）
- 不再返回完整 state
- 由 workflow/builder 层负责 state merge
"""

import json
from typing import Dict, Any, List
from utils.logger import get_logger
from graph.state import TeachingState
from llm.factory import get_llm_for_state

logger = get_logger(__name__)


# content_node 需要生成的字段
CONTENT_REQUIRED_FIELDS = [
    "practice_design",
    "blackboard_design",
    "homework"
]


def normalize_content_output(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    标准化 content_node 输出

    确保输出符合预期结构
    """
    result = {}

    # 练习题设计
    result["practice_design"] = raw_data.get("practice_design", {
        "basic": [],
        "intermediate": [],
        "advanced": []
    })

    # 板书设计
    result["blackboard_design"] = raw_data.get("blackboard_design", {
        "layout": "",
        "main_content": [],
        "key_formulas": [],
        "diagrams": []
    })

    # 作业设计
    result["homework"] = raw_data.get("homework", [])

    # 教师话术（可选）
    if "teacher_script" in raw_data:
        result["teacher_script"] = raw_data["teacher_script"]

    # 易错点分析（可选）
    if "common_mistakes" in raw_data:
        result["common_mistakes"] = raw_data["common_mistakes"]

    # 教学案例（可选）
    if "examples" in raw_data:
        result["examples"] = raw_data["examples"]

    return result


def validate_content_output(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    验证 content_node 输出

    返回: (是否通过, 问题列表)
    """
    issues = []

    # 检查必需字段
    for field in CONTENT_REQUIRED_FIELDS:
        if field not in data:
            issues.append(f"缺少必需字段: {field}")

    # 检查 practice_design
    practice = data.get("practice_design", {})
    basic_count = len(practice.get("basic", []))
    intermediate_count = len(practice.get("intermediate", []))
    advanced_count = len(practice.get("advanced", []))

    if basic_count < 2:
        issues.append(f"基础题只有{basic_count}道，要求至少2道")
    if intermediate_count < 1:
        issues.append(f"中等题只有{intermediate_count}道，要求至少1道")
    if advanced_count < 1:
        issues.append(f"拓展题只有{advanced_count}道，要求至少1道")

    # 检查每道题的结构
    for level in ["basic", "intermediate", "advanced"]:
        for i, problem in enumerate(practice.get(level, [])):
            if not problem.get("question"):
                issues.append(f"{level}题{i+1}缺少question字段")
            if not problem.get("answer"):
                issues.append(f"{level}题{i+1}缺少answer字段")

    # 检查 blackboard_design
    blackboard = data.get("blackboard_design", {})
    if not blackboard.get("layout"):
        issues.append("blackboard_design缺少layout字段")
    if not blackboard.get("main_content"):
        issues.append("blackboard_design缺少main_content字段")

    # 检查 homework
    homework = data.get("homework", [])
    if len(homework) < 1:
        issues.append("homework至少需要1道作业")

    # 检查 JSON 大小（估算）
    import json
    json_str = json.dumps(data, ensure_ascii=False)
    token_estimate = len(json_str) // 2
    if token_estimate > 4000:
        issues.append(f"JSON过大(约{token_estimate}tokens)，要求小于4000tokens")

    return len(issues) == 0, issues


def content_node(state: TeachingState) -> Dict[str, Any]:
    """
    教学内容生成节点

    根据教学计划骨架和互动设计，生成具体的教学内容

    重构后返回 partial update:
    - 成功时: {"content": content_data}
    - 失败时: {"content": default_content, "error_count": state.error_count + 1}
    """
    topic = state.topic
    grade = state.grade
    plan = state.plan
    design = state.design

    logger.info(f"开始生成教学内容: 主题={topic}, 年级={grade}")

    # 读取 Prompt 模板
    try:
        with open("prompts/content.txt", "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logger.error("未找到 content.txt prompt 文件")
        return _handle_error(state, "Prompt file not found")

    # 构建 Prompt
    plan_summary = json.dumps(plan, ensure_ascii=False, indent=2)
    design_summary = json.dumps(design, ensure_ascii=False, indent=2)
    prompt = prompt_template.replace('{topic}', topic).replace('{grade}', grade).replace('{plan}', plan_summary).replace('{design}', design_summary)

    # 定义 Schema
    expected_schema = _get_content_schema()

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
                    required_fields=CONTENT_REQUIRED_FIELDS
                )

                # 标准化输出
                content_data = normalize_content_output(raw_data)

                # 验证输出
                is_valid, issues = validate_content_output(content_data)

                if is_valid:
                    logger.info("成功生成教学内容")
                    # 返回 partial update，只包含 content 字段
                    return {"content": content_data}
                else:
                    logger.warning(f"输出验证未通过 (尝试 {attempt + 1}/{max_retries}):")
                    for issue in issues:
                        logger.warning(f"  - {issue}")

                    # 如果是最后一次尝试，使用当前结果
                    if attempt == max_retries - 1:
                        logger.warning("达到最大重试次数，使用当前结果")
                        return {"content": content_data}

            except Exception as e:
                logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
                if attempt == max_retries - 1:
                    raise

        # 如果所有尝试都失败，创建默认值
        logger.warning("所有重试都失败，使用默认教学内容")
        content_data = _create_default_content()
        return {"content": content_data}

    except Exception as e:
        logger.error(f"content_node 执行失败: {e}")
        return _handle_error(state, str(e))


def _get_system_prompt() -> str:
    """获取系统提示"""
    return (
        "你是一位经验丰富的教学内容设计师。\n"
        "你的任务是根据教学计划骨架和互动设计，生成具体的教学内容。\n\n"
        "【重要规则】\n"
        "1. practice_design 必须包含分层练习题：basic（基础）、intermediate（中等）、advanced（拓展）\n"
        "2. 每道题必须包含：question（题目）、answer（答案）、purpose（考察目标）、time（建议用时）\n"
        "3. blackboard_design 必须包含：layout（布局）、main_content（主板书）、key_formulas（核心公式）\n"
        "4. homework 必须包含：type（必做/选做）、content（作业内容）、purpose（作业目的）\n"
        "5. 保持输出简洁，总长度控制在3500tokens以内\n\n"
        "【输出格式】\n"
        "必须严格按照 JSON 格式输出，包含以下字段：\n"
        "- practice_design: 练习题设计\n"
        "- blackboard_design: 板书设计\n"
        "- homework: 作业设计\n"
        "- common_mistakes: 易错点分析（可选）\n"
        "- teacher_script: 教师话术（可选）\n"
    )


def _get_content_schema() -> Dict[str, Any]:
    """获取 content_node 的 JSON Schema"""
    return {
        "type": "object",
        "properties": {
            "practice_design": {
                "type": "object",
                "properties": {
                    "basic": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": {"type": "string"},
                                "answer": {"type": "string"},
                                "purpose": {"type": "string"},
                                "time": {"type": "string"}
                            },
                            "required": ["question", "answer", "purpose", "time"]
                        }
                    },
                    "intermediate": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": {"type": "string"},
                                "answer": {"type": "string"},
                                "purpose": {"type": "string"},
                                "time": {"type": "string"}
                            },
                            "required": ["question", "answer", "purpose", "time"]
                        }
                    },
                    "advanced": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": {"type": "string"},
                                "answer": {"type": "string"},
                                "purpose": {"type": "string"},
                                "time": {"type": "string"}
                            },
                            "required": ["question", "answer", "purpose", "time"]
                        }
                    }
                },
                "required": ["basic", "intermediate", "advanced"]
            },
            "blackboard_design": {
                "type": "object",
                "properties": {
                    "layout": {"type": "string"},
                    "main_content": {"type": "array", "items": {"type": "string"}},
                    "key_formulas": {"type": "array", "items": {"type": "string"}},
                    "diagrams": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["layout", "main_content"]
            },
            "homework": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "content": {"type": "string"},
                        "purpose": {"type": "string"}
                    },
                    "required": ["type", "content", "purpose"]
                }
            },
            "common_mistakes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "mistake": {"type": "string"},
                        "frequency": {"type": "string"},
                        "cause": {"type": "string"},
                        "correction": {"type": "string"},
                        "example": {"type": "string"}
                    }
                }
            },
            "teacher_script": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "stage": {"type": "string"},
                        "script": {"type": "string"}
                    }
                }
            },
            "examples": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "explanation": {"type": "string"}
                    }
                }
            }
        },
        "required": CONTENT_REQUIRED_FIELDS
    }


def _create_default_content() -> Dict[str, Any]:
    """创建默认的教学内容"""
    return {
        "practice_design": {
            "basic": [
                {
                    "question": "基础练习题",
                    "answer": "参考答案",
                    "purpose": "考察基本概念",
                    "time": "2分钟"
                },
                {
                    "question": "基础练习题2",
                    "answer": "参考答案",
                    "purpose": "考察基本计算",
                    "time": "2分钟"
                }
            ],
            "intermediate": [
                {
                    "question": "中等练习题",
                    "answer": "参考答案",
                    "purpose": "考察应用能力",
                    "time": "3分钟"
                }
            ],
            "advanced": [
                {
                    "question": "拓展练习题",
                    "answer": "参考答案",
                    "purpose": "考察综合能力",
                    "time": "5分钟"
                }
            ]
        },
        "blackboard_design": {
            "layout": "左中右三区布局",
            "main_content": ["核心概念", "重要公式", "解题步骤"],
            "key_formulas": ["公式1", "公式2"],
            "diagrams": ["图示说明"]
        },
        "homework": [
            {
                "type": "必做",
                "content": "基础作业",
                "purpose": "巩固课堂知识"
            },
            {
                "type": "选做",
                "content": "拓展作业",
                "purpose": "提升综合能力"
            }
        ],
        "common_mistakes": [
            {
                "mistake": "典型错误",
                "frequency": "高",
                "cause": "概念理解不清",
                "correction": "强调关键点",
                "example": "纠正示例"
            }
        ]
    }


def _handle_error(state: TeachingState, error_msg: str) -> Dict[str, Any]:
    """
    处理错误情况

    返回 partial update，包含默认 content 和递增的 error_count
    """
    logger.error(f"content_node 错误: {error_msg}")

    default_content = _create_default_content()
    default_content["error"] = error_msg

    # 返回 partial update，只包含 content 和 error_count
    return {
        "content": default_content,
        "error_count": state.error_count + 1
    }


# 注册节点到工作流
def create_content_node():
    """创建 content 节点函数"""
    return content_node
