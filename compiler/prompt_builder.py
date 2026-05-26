"""
prompt_builder - 构建编译器 Prompt

将 Cognitive IR 各组件组装为编译器的输入 Prompt。
包含大小限制，防止超出 LLM 上下文窗口。
"""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# 最大 prompt 字符数（约 8000 tokens，留余量给 system prompt 和输出）
MAX_PROMPT_CHARS = 24000


def build_compiler_prompt(
    cognitive_flow: Dict[str, Any],
    knowledge_structure: Dict[str, Any],
    interaction_design: Dict[str, Any],
    practice_design: Dict[str, Any],
    misconception_model: Dict[str, Any],
    blackboard_design: Dict[str, Any],
    homework: List[Dict[str, Any]],
    topic: str,
    grade: str,
) -> str:
    """
    将 Cognitive IR 各组件组装为编译器 Prompt。

    包含大小限制：如果总长度超出限制，会截断低优先级部分。

    Args:
        cognitive_flow: 认知推进路线
        knowledge_structure: 知识结构
        interaction_design: 互动设计
        practice_design: 练习题设计
        misconception_model: 易错点模型
        blackboard_design: 板书设计
        homework: 作业设计
        topic: 教学主题
        grade: 年级

    Returns:
        组装好的 Prompt 字符串
    """
    # 按优先级组装各部分（高优先级在前）
    sections = []

    # 必须包含
    sections.append(("基本信息", f"【教学主题】{topic}\n【适用年级】{grade}"))
    sections.append(("认知推进路线", _safe_json(cognitive_flow, "认知推进路线")))

    # 高价值
    if knowledge_structure:
        sections.append(("知识结构分析", _safe_json(knowledge_structure, "知识结构")))

    if interaction_design:
        sections.append(("互动设计策略", _safe_json(interaction_design, "互动设计")))

    # 中等价值
    if practice_design:
        sections.append(("练习题设计", _safe_json(practice_design, "练习题")))

    if homework:
        sections.append(("作业设计", _safe_json(homework, "作业")))

    # 低优先级（可截断）
    if misconception_model:
        sections.append(("易错点模型", _safe_json(misconception_model, "易错点")))

    if blackboard_design:
        sections.append(("板书设计", _safe_json(blackboard_design, "板书")))

    # 组装并检查大小
    parts = []
    total_chars = 0

    for name, content in sections:
        section_text = f"【{name}】\n{content}\n"
        section_chars = len(section_text)

        if total_chars + section_chars > MAX_PROMPT_CHARS:
            logger.warning(f"Prompt 已达大小限制，截断了 [{name}] 部分 ({section_chars} chars)")
            parts.append(f"【{name}】（因长度限制已省略）\n")
            continue

        parts.append(section_text)
        total_chars += section_chars

    prompt = "\n".join(parts)
    logger.info(f"Compiler prompt 大小: {total_chars} chars / {MAX_PROMPT_CHARS} max")
    return prompt


def _safe_json(data: Any, label: str) -> str:
    """安全 JSON 序列化，处理 None 和序列化错误"""
    if data is None:
        return "（无数据）"
    try:
        result = json.dumps(data, ensure_ascii=False, indent=2)
        if result == "{}" or result == "[]":
            return "（空）"
        return result
    except (TypeError, ValueError) as e:
        logger.warning(f"JSON 序列化失败 [{label}]: {e}")
        return f"（序列化错误: {e}）"
