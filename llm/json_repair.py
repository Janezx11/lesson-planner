"""
统一 JSON 修复逻辑

从 Claude/Qwen/LongCat 三个客户端中提取并合并的 JSON 解析和修复策略。
所有 LLM 客户端共用此模块，避免代码重复。
"""

import json
import re
from typing import Dict, Any

from utils.logger import get_logger
from utils.parser import safe_parse_json, JSONParsingError

logger = get_logger(__name__)


def _escape_newlines_in_strings(text: str) -> str:
    """只转义 JSON 字符串值内部的换行符，不影响 JSON 结构。"""
    result = []
    in_string = False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '"' and (i == 0 or text[i - 1] != "\\"):
            in_string = not in_string
            result.append(ch)
        elif ch == "\n" and in_string:
            result.append("\\n")
        else:
            result.append(ch)
        i += 1
    return "".join(result)


def extract_json_object(text: str) -> str:
    """从 LLM 响应文本中提取第一个 JSON 对象。

    Args:
        text: LLM 返回的原始文本

    Returns:
        提取出的 JSON 字符串

    Raises:
        JSONParsingError: 找不到有效的 JSON 结构
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise JSONParsingError(f"无法在文本中找到有效的 JSON 结构: {text[:100]}...")
    return text[start : end + 1]


def repair_json(text: str) -> str:
    """尝试修复无效的 JSON 文本。

    合并了所有客户端的修复策略：
    - 单引号替换为双引号
    - 尾随逗号移除
    - 缺少逗号修复（值后跟 key 之间）
    - 未转义换行符修复
    - 括号平衡

    Args:
        text: 可能损坏的 JSON 字符串

    Returns:
        修复后的 JSON 字符串
    """
    fixed = text

    # 1. 替换单引号为双引号（key 周围）
    fixed = re.sub(r"(?<=[{\[,])\s*'([^']*)'\s*:", r' "\1":', fixed)
    fixed = re.sub(r":\s*'([^']*)'", r': "\1"', fixed)

    # 2. 移除尾随逗号（在 } 或 ] 之前）
    fixed = re.sub(r",\s*([}\]])", r"\1", fixed)

    # 3. 移除开头逗号（在 { 或 [ 之后）
    fixed = re.sub(r"([{\[])\s*,", r"\1", fixed)

    # 4. 修复缺少逗号 — 值后面紧跟 key（最常见的 LLM 错误）
    # "value"\n  "key":  →  "value",\n  "key":
    fixed = re.sub(r'"\s*\n(\s*)"', r'",\n\1"', fixed)
    # "value"  "key":  →  "value", "key":（同行）
    fixed = re.sub(r'"\s+"(\w)', r'", "\1', fixed)
    # } 后紧跟 "key":  →  }, "key":
    fixed = re.sub(r'}\s*\n(\s*)"', r'},\n\1"', fixed)
    # ] 后紧跟 "key":  →  ], "key":
    fixed = re.sub(r']\s*\n(\s*)"', r'],\n\1"', fixed)
    # } 后紧跟 {  →  }, {
    fixed = re.sub(r'}\s*\n(\s*)\{', r'},\n\1{', fixed)
    # ] 后紧跟 {  →  ], {
    fixed = re.sub(r']\s*\n(\s*)\{', r'],\n\1{', fixed)

    # 5. 修复字符串值内部的未转义换行符
    # 只替换字符串值内部的换行，不影响 JSON 结构
    fixed = _escape_newlines_in_strings(fixed)

    # 6. 平衡方括号（先于大括号，保证嵌套顺序正确）
    open_bracket = fixed.count("[")
    close_bracket = fixed.count("]")
    if open_bracket > close_bracket:
        fixed += "]" * (open_bracket - close_bracket)
    elif close_bracket > open_bracket:
        for _ in range(close_bracket - open_bracket):
            idx = fixed.rfind("]")
            if idx != -1:
                fixed = fixed[:idx] + fixed[idx + 1 :]

    # 7. 平衡大括号（在方括号之后，保证 ] 在 } 之前）
    open_brace = fixed.count("{")
    close_brace = fixed.count("}")
    if open_brace > close_brace:
        fixed += "}" * (open_brace - close_brace)
    elif close_brace > open_brace:
        for _ in range(close_brace - open_brace):
            idx = fixed.rfind("}")
            if idx != -1:
                fixed = fixed[:idx] + fixed[idx + 1 :]

    return fixed


def parse_llm_json(raw_text: str) -> Dict[str, Any]:
    """解析 LLM 返回的 JSON 文本，带 4 层容错。

    解析链：
    1. 提取 + 直接 json.loads
    2. 提取 + 修复 + json.loads
    3. safe_parse_json（utils.parser）
    4. 正则兜底 + 修复

    Args:
        raw_text: LLM 返回的原始文本

    Returns:
        解析后的字典

    Raises:
        JSONParsingError: 所有解析策略都失败
    """
    # 尝试 1: 直接解析
    try:
        json_str = extract_json_object(raw_text)
        return json.loads(json_str)
    except (json.JSONDecodeError, JSONParsingError):
        pass

    # 尝试 2: 修复后解析
    try:
        json_str = extract_json_object(raw_text)
        repaired = repair_json(json_str)
        return json.loads(repaired)
    except (json.JSONDecodeError, JSONParsingError):
        pass

    # 尝试 3: safe_parse_json
    try:
        json_str = extract_json_object(raw_text)
        result = safe_parse_json(json_str)
        if "error" not in result:
            return result
    except Exception:
        pass

    # 尝试 4: 正则兜底 + 修复
    try:
        match = re.search(r"\{[\s\S]*\}", raw_text)
        if match:
            repaired = repair_json(match.group(0))
            return json.loads(repaired)
    except (json.JSONDecodeError, Exception):
        pass

    raise JSONParsingError(f"所有 JSON 解析策略都失败: {raw_text[:200]}...")