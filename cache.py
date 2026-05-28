"""
教案缓存模块

文件缓存（JSON），避免相同主题重复调用 LLM API。

缓存 key：sha256(topic + grade + provider)
缓存目录：.cache/
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from utils.logger import get_logger

logger = get_logger(__name__)

CACHE_DIR = Path(".cache")


def _ensure_cache_dir() -> None:
    """确保缓存目录存在"""
    CACHE_DIR.mkdir(exist_ok=True)


def get_cache_key(topic: str, grade: str, provider: str) -> str:
    """生成缓存 key。

    Args:
        topic: 教学主题
        grade: 年级
        provider: LLM 提供商

    Returns:
        sha256 哈希的前 16 位
    """
    raw = f"{topic.strip().lower()}|{grade.strip().lower()}|{provider.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def get_cached(key: str) -> Optional[Dict[str, Any]]:
    """读取缓存。

    Args:
        key: 缓存 key

    Returns:
        缓存的数据，未命中时返回 None
    """
    _ensure_cache_dir()
    path = CACHE_DIR / f"{key}.json"

    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"缓存命中: {key}")
        return data
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"缓存读取失败: {e}")
        return None


def set_cached(key: str, data: Dict[str, Any]) -> bool:
    """写入缓存。

    错误结果（含 "error" key）不缓存。

    Args:
        key: 缓存 key
        data: 要缓存的数据

    Returns:
        是否成功写入
    """
    if "error" in data:
        logger.debug("错误结果不缓存")
        return False

    _ensure_cache_dir()
    path = CACHE_DIR / f"{key}.json"

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"缓存已写入: {key}")
        return True
    except IOError as e:
        logger.warning(f"缓存写入失败: {e}")
        return False


def clear_cache() -> int:
    """清除所有缓存。

    Returns:
        删除的文件数
    """
    _ensure_cache_dir()
    count = 0
    for path in CACHE_DIR.glob("*.json"):
        try:
            path.unlink()
            count += 1
        except IOError as e:
            logger.warning(f"删除缓存文件失败: {e}")
    logger.info(f"已清除 {count} 个缓存文件")
    return count


def cache_stats() -> Dict[str, Any]:
    """获取缓存统计信息。

    Returns:
        缓存统计字典
    """
    _ensure_cache_dir()
    files = list(CACHE_DIR.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files)

    return {
        "count": len(files),
        "total_size_kb": round(total_size / 1024, 1),
        "cache_dir": str(CACHE_DIR),
    }


def list_cached() -> List[Dict[str, Any]]:
    """列出所有缓存条目。

    Returns:
        缓存条目列表，每项包含 key, topic, grade, provider, generated_at, size_kb
    """
    _ensure_cache_dir()
    entries = []

    for path in sorted(CACHE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            meta = data.get("metadata", {})
            entries.append({
                "key": path.stem,
                "topic": meta.get("topic", "未知"),
                "grade": meta.get("grade", "未知"),
                "provider": meta.get("llm_provider", "未知"),
                "generated_at": meta.get("generated_at", "未知"),
                "size_kb": round(path.stat().st_size / 1024, 1),
            })
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"读取缓存条目失败 {path.name}: {e}")
            continue

    return entries


def delete_cached(key: str) -> bool:
    """删除指定缓存。

    Args:
        key: 缓存 key

    Returns:
        是否成功删除
    """
    _ensure_cache_dir()
    path = CACHE_DIR / f"{key}.json"

    if not path.exists():
        return False

    try:
        path.unlink()
        logger.info(f"已删除缓存: {key}")
        return True
    except IOError as e:
        logger.warning(f"删除缓存失败: {e}")
        return False
