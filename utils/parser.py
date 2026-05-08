"""
JSON 解析和错误处理工具

提供统一的 JSON 解析、验证和错误处理功能，
用于处理 Claude API 的输出。
"""

import json
import logging
from typing import Dict, Any, Optional, Union, List
from functools import wraps

logger = logging.getLogger(__name__)


class JSONParsingError(Exception):
    """JSON 解析错误"""
    pass


def retry_on_json_error(max_retries: int = 3):
    """
    装饰器：在 JSON 解析错误时重试

    Args:
        max_retries: 最大重试次数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"第 {attempt + 1} 次尝试失败，将在 1 秒后重试: {e}")
                        import time
                        time.sleep(1)
                    else:
                        logger.error(f"所有 {max_retries} 次尝试都失败了")

            raise last_exception
        return wrapper
    return decorator


def safe_parse_json(text: str, fallback_key: str = "raw_response") -> Dict[str, Any]:
    """
    安全地解析 JSON 文本

    Args:
        text: 需要解析的文本
        fallback_key: 当解析失败时的回退键名

    Returns:
        解析后的字典对象

    Raises:
        ValueError: 无法解析且无有效结构
    """
    if not text or not isinstance(text, str):
        return {"error": "输入为空或不是字符串", fallback_key: str(text)}

    # 清理文本
    cleaned_text = text.strip()

    # 查找可能的 JSON 开始和结束位置
    start_idx = find_json_start(cleaned_text)
    end_idx = find_json_end(cleaned_text)

    if start_idx == -1 or end_idx == -1:
        # 没有有效的 JSON 结构，返回原始文本
        logger.warning(f"未找到有效的 JSON 结构: {cleaned_text[:100]}...")
        return {"error": "未找到有效的 JSON 结构", fallback_key: cleaned_text}

    # 提取 JSON 部分
    json_str = cleaned_text[start_idx:end_idx+1]

    try:
        parsed_data = json.loads(json_str)
        logger.debug("成功解析 JSON")
        return parsed_data
    except json.JSONDecodeError as e:
        logger.warning(f"JSON 解析失败: {e}, 尝试修复...")
        return repair_and_parse_json(json_str, fallback_key)


def find_json_start(text: str) -> int:
    """查找 JSON 的开始位置"""
    patterns = ['{', '{"', '{ "']
    min_idx = len(text)

    for pattern in patterns:
        idx = text.find(pattern)
        if idx != -1 and idx < min_idx:
            min_idx = idx

    return min_idx if min_idx != len(text) else -1


def find_json_end(text: str) -> int:
    """查找 JSON 的结束位置"""
    # 从后往前找 } 或 ]
    for i in range(len(text) - 1, -1, -1):
        char = text[i]
        if char in ['}', ']']:
            # 检查是否是完整的 JSON 对象或数组
            open_brace_count = 0
            close_brace_count = 0

            for j in range(i, -1, -1):
                if text[j] == '{':
                    open_brace_count += 1
                elif text[j] == '}':
                    close_brace_count += 1
                elif text[j] == '[':
                    open_bracket_count += 1
                elif text[j] == ']':
                    close_bracket_count += 1

                if (open_brace_count > 0 and close_brace_count > 0 and
                    open_brace_count == close_brace_count):
                    return i

    return -1


def repair_and_parse_json(json_str: str, fallback_key: str) -> Dict[str, Any]:
    """
    修复并解析 JSON 字符串

    Args:
        json_str: 需要修复的 JSON 字符串
        fallback_key: 回退键名

    Returns:
        修复后的字典对象
    """
    original_error = None

    # 尝试多种修复策略
    repairs = [
        # 策略 1: 添加缺失的引号
        lambda s: s.replace('\n', '').replace('\r', ''),
        # 策略 2: 修复单引号
        lambda s: s.replace("'", '"'),
        # 策略 3: 修复尾随逗号
        lambda s: re.sub(r',\s*}', '}', s),
        lambda s: re.sub(r',\s*]', ']', s),
        # 策略 4: 修复不完整的 JSON
        lambda s: ensure_complete_json(s),
    ]

    import re

    for i, repair_func in enumerate(repairs):
        try:
            repaired_str = repair_func(json_str)
            parsed = json.loads(repaired_str)
            logger.info(f"通过第 {i+1} 种修复策略成功解析 JSON")
            return parsed
        except json.JSONDecodeError as e:
            original_error = e
            continue

    # 所有修复策略都失败，创建最小结构
    logger.error(f"所有修复策略都失败: {original_error}")
    return {
        "error": "无法修复 JSON",
        "repair_attempts": len(repairs),
        "original_error": str(original_error),
        fallback_key: json_str
    }


def ensure_complete_json(json_str: str) -> str:
    """
    确保 JSON 字符串是完整的

    Args:
        json_str: 可能不完整的 JSON 字符串

    Returns:
        完整的 JSON 字符串
    """
    # 统计括号和引号
    brace_count = 0
    bracket_count = 0
    quote_count = 0
    escaped = False

    for char in json_str:
        if escaped:
            escaped = False
            continue

        if char == '\\':
            escaped = True
            continue

        if char == '"':
            quote_count += 1
        elif char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
        elif char == '[':
            bracket_count += 1
        elif char == ']':
            bracket_count -= 1

    # 如果括号不平衡，添加缺失的闭合括号
    result = json_str
    while brace_count > 0 or bracket_count > 0:
        if brace_count > 0:
            result += '}'
            brace_count -= 1
        if bracket_count > 0:
            result += ']'
            bracket_count -= 1

    return result


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """
    验证必需字段是否存在

    Args:
        data: 数据字典
        required_fields: 必需字段列表

    Returns:
        是否所有必需字段都存在
    """
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]

    if missing_fields:
        logger.warning(f"缺少必需字段: {missing_fields}")
        return False

    return True


def merge_dicts_safe(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    安全地合并两个字典

    Args:
        dict1: 第一个字典
        dict2: 第二个字典

    Returns:
        合并后的字典
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # 递归合并嵌套字典
            result[key] = merge_dicts_safe(result[key], value)
        else:
            result[key] = value

    return result


def get_llm_provider() -> str:
    """获取当前使用的 LLM 提供商"""
    import os
    return os.getenv("LLM_PROVIDER", "claude")


def extract_json_from_markdown(markdown_text: str) -> str:
    """
    从 Markdown 文本中提取 JSON

    Args:
        markdown_text: 包含 JSON 的 Markdown 文本

    Returns:
        提取出的 JSON 字符串
    """
    import re

    # 匹配 ```json ... ``` 块
    json_pattern = r'```json\s*(.*?)\s*```'
    match = re.search(json_pattern, markdown_text, re.DOTALL)

    if match:
        return match.group(1).strip()

    # 如果没有找到 ```json 块，尝试查找任何 ``` 块
    any_code_pattern = r'```\s*(.*?)\s*```'
    match = re.search(any_code_pattern, markdown_text, re.DOTALL)

    if match:
        return match.group(1).strip()

    # 最后尝试直接查找 JSON 对象
    json_obj_pattern = r'\{.*\}'
    match = re.search(json_obj_pattern, markdown_text, re.DOTALL)

    if match:
        return match.group(0).strip()

    return markdown_text