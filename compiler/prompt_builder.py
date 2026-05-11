"""
prompt_builder - 构建编译器 Prompt

将 Cognitive IR 各组件组装为编译器的输入 Prompt。
"""

import json
from typing import Dict, Any, List


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
    parts = []

    # 基本信息
    parts.append(f"【教学主题】{topic}")
    parts.append(f"【适用年级】{grade}")
    parts.append("")

    # 认知推进路线
    parts.append("【认知推进路线（AI 内部，需要转换为教师语言）】")
    parts.append(json.dumps(cognitive_flow, ensure_ascii=False, indent=2))
    parts.append("")

    # 知识结构
    if knowledge_structure:
        parts.append("【知识结构分析】")
        parts.append(json.dumps(knowledge_structure, ensure_ascii=False, indent=2))
        parts.append("")

    # 互动设计
    if interaction_design:
        parts.append("【互动设计策略】")
        parts.append(json.dumps(interaction_design, ensure_ascii=False, indent=2))
        parts.append("")

    # 练习题
    if practice_design:
        parts.append("【练习题设计】")
        parts.append(json.dumps(practice_design, ensure_ascii=False, indent=2))
        parts.append("")

    # 易错点
    if misconception_model:
        parts.append("【易错点模型】")
        parts.append(json.dumps(misconception_model, ensure_ascii=False, indent=2))
        parts.append("")

    # 板书
    if blackboard_design:
        parts.append("【板书设计】")
        parts.append(json.dumps(blackboard_design, ensure_ascii=False, indent=2))
        parts.append("")

    # 作业
    if homework:
        parts.append("【作业设计】")
        parts.append(json.dumps(homework, ensure_ascii=False, indent=2))
        parts.append("")

    return "\n".join(parts)
