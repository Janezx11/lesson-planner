"""
教案库模块

结构化存储生成的教案，文件名人类可读。
同时承担缓存职责（相同参数跳过 LLM 调用）。

目录结构：
    教案库/
    ├── index.json                          ← 索引（cache key → 文件路径）
    ├── 2026-06-01_二次函数_高二.json
    ├── 2026-06-01_牛顿第二定律_高一.json
    └── ...
"""

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from utils.logger import get_logger

logger = get_logger(__name__)

PLANS_DIR = Path("教案库")
INDEX_FILE = PLANS_DIR / "index.json"

# 旧缓存目录（用于迁移）
_OLD_CACHE_DIR = Path(".cache")


def _ensure_dir() -> None:
    """确保教案库目录存在"""
    PLANS_DIR.mkdir(exist_ok=True)


def _load_index() -> Dict[str, Dict[str, Any]]:
    """加载索引文件"""
    if not INDEX_FILE.exists():
        return {}
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_index(index: Dict[str, Dict[str, Any]]) -> None:
    """保存索引文件"""
    _ensure_dir()
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def _safe_filename(text: str) -> str:
    """将文本转换为文件系统安全的名称"""
    # 保留中文、字母、数字、下划线、连字符
    safe = re.sub(r'[^\w一-鿿\-]', '_', text.strip())
    # 去掉连续下划线
    safe = re.sub(r'_+', '_', safe).strip('_')
    return safe[:30]  # 限制长度


def _make_filename(topic: str, grade: str) -> str:
    """生成可读的文件名：YYYY-MM-DD_主题_年级.json"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    topic_safe = _safe_filename(topic)
    grade_safe = _safe_filename(grade)
    return f"{date_str}_{topic_safe}_{grade_safe}.json"


def get_cache_key(topic: str, grade: str, provider: str, duration: str = "45分钟", level: str = "普通") -> str:
    """生成缓存 key。

    Args:
        topic: 教学主题
        grade: 年级
        provider: LLM 提供商
        duration: 课时时长
        level: 班级水平

    Returns:
        sha256 哈希的前 16 位
    """
    raw = f"{topic.strip().lower()}|{grade.strip().lower()}|{provider.strip().lower()}|{duration.strip()}|{level.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def get_cached(key: str) -> Optional[Dict[str, Any]]:
    """读取缓存。

    Args:
        key: 缓存 key

    Returns:
        缓存的数据，未命中时返回 None
    """
    index = _load_index()
    entry = index.get(key)

    if not entry:
        return None

    path = PLANS_DIR / entry["file"]
    if not path.exists():
        # 索引指向的文件不存在，清理索引
        logger.warning(f"索引指向的文件不存在: {path}")
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"缓存命中: {key} -> {entry['file']}")
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

    _ensure_dir()

    # 从 metadata 提取信息生成文件名
    meta = data.get("metadata", {})
    topic = meta.get("topic", "未知主题")
    grade = meta.get("grade", "未知年级")
    filename = _make_filename(topic, grade)

    # 如果同名文件已存在，加序号
    path = PLANS_DIR / filename
    counter = 1
    while path.exists():
        name_no_ext = filename.rsplit(".", 1)[0]
        path = PLANS_DIR / f"{name_no_ext}_{counter}.json"
        counter += 1

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 更新索引
        index = _load_index()
        index[key] = {
            "file": path.name,
            "topic": topic,
            "grade": grade,
            "provider": meta.get("llm_provider", ""),
            "generated_at": meta.get("generated_at", datetime.now().isoformat()),
            "size_kb": round(path.stat().st_size / 1024, 1),
        }
        _save_index(index)

        logger.info(f"教案已保存: {path.name} (key={key})")
        return True
    except IOError as e:
        logger.warning(f"写入失败: {e}")
        return False


def clear_cache() -> int:
    """清除所有教案。

    Returns:
        删除的文件数
    """
    _ensure_dir()
    count = 0
    for path in PLANS_DIR.glob("*.json"):
        if path.name == "index.json":
            continue
        try:
            path.unlink()
            count += 1
        except IOError as e:
            logger.warning(f"删除文件失败: {e}")

    # 清空索引
    _save_index({})

    logger.info(f"已清除 {count} 个教案文件")
    return count


def cache_stats() -> Dict[str, Any]:
    """获取教案库统计信息。

    Returns:
        统计字典
    """
    _ensure_dir()
    files = [f for f in PLANS_DIR.glob("*.json") if f.name != "index.json"]
    total_size = sum(f.stat().st_size for f in files)

    return {
        "count": len(files),
        "total_size_kb": round(total_size / 1024, 1),
        "cache_dir": str(PLANS_DIR),
    }


def list_cached() -> List[Dict[str, Any]]:
    """列出所有教案。

    Returns:
        教案列表，每项包含 key, topic, grade, provider, generated_at, size_kb
    """
    index = _load_index()
    entries = []

    for key, entry in index.items():
        path = PLANS_DIR / entry["file"]
        if not path.exists():
            continue
        entries.append({
            "key": key,
            "topic": entry.get("topic", "未知"),
            "grade": entry.get("grade", "未知"),
            "provider": entry.get("provider", "未知"),
            "generated_at": entry.get("generated_at", "未知"),
            "size_kb": round(path.stat().st_size / 1024, 1),
        })

    # 按生成时间倒序
    entries.sort(key=lambda e: e["generated_at"], reverse=True)
    return entries


def delete_cached(key: str) -> bool:
    """删除指定教案。

    Args:
        key: 缓存 key

    Returns:
        是否成功删除
    """
    index = _load_index()
    entry = index.get(key)

    if not entry:
        return False

    path = PLANS_DIR / entry["file"]
    try:
        if path.exists():
            path.unlink()
        del index[key]
        _save_index(index)
        logger.info(f"已删除教案: {entry['file']} (key={key})")
        return True
    except IOError as e:
        logger.warning(f"删除失败: {e}")
        return False


def get_plans_dir() -> str:
    """返回教案库目录路径（供 Web UI 打开文件夹用）"""
    _ensure_dir()
    return str(PLANS_DIR.resolve())


# ─── 课后反思 ─────────────────────────────────────────────────

def add_reflection(
    key: str,
    what_worked: str = "",
    what_failed: str = "",
    student_reaction: str = "",
    next_adjustment: str = "",
) -> bool:
    """为指定教案添加课后反思。

    Args:
        key: 缓存 key
        what_worked: 效果好的环节
        what_failed: 效果差的环节
        student_reaction: 学生反应
        next_adjustment: 下次想怎么调整

    Returns:
        是否成功保存
    """
    index = _load_index()
    entry = index.get(key)
    if not entry:
        logger.warning(f"教案不存在: {key}")
        return False

    path = PLANS_DIR / entry["file"]
    if not path.exists():
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        reflections = data.get("reflections", [])
        reflections.append({
            "timestamp": datetime.now().isoformat(),
            "what_worked": what_worked,
            "what_failed": what_failed,
            "student_reaction": student_reaction,
            "next_adjustment": next_adjustment,
        })
        data["reflections"] = reflections

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"已添加反思: {entry['file']}")
        return True
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"添加反思失败: {e}")
        return False


def get_reflections_for_topic(topic: str, limit: int = 5) -> List[Dict[str, str]]:
    """获取同主题教案的历史反思（用于生成时注入 prompt）。

    Args:
        topic: 教学主题
        limit: 最多返回几条反思

    Returns:
        反思列表，按时间倒序
    """
    index = _load_index()
    results = []

    topic_lower = topic.strip().lower()

    for key, entry in index.items():
        # 模糊匹配主题
        entry_topic = entry.get("topic", "").lower()
        if topic_lower not in entry_topic and entry_topic not in topic_lower:
            continue

        path = PLANS_DIR / entry["file"]
        if not path.exists():
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            reflections = data.get("reflections", [])
            for r in reflections:
                r["_topic"] = entry.get("topic", "")
                r["_grade"] = entry.get("grade", "")
                results.append(r)
        except (json.JSONDecodeError, IOError):
            continue

    # 按时间倒序，取最近的 limit 条
    results.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return results[:limit]


def format_reflections_for_prompt(reflections: List[Dict[str, str]]) -> str:
    """将历史反思格式化为 prompt 注入文本。

    Args:
        reflections: 反思列表

    Returns:
        格式化的文本，可直接注入 prompt
    """
    if not reflections:
        return ""

    lines = ["【历史教学反思 — 请参考以下经验】"]
    for i, r in enumerate(reflections, 1):
        topic = r.get("_topic", "")
        grade = r.get("_grade", "")
        lines.append(f"\n反思{i}（{topic} {grade}）：")
        if r.get("what_worked"):
            lines.append(f"  效果好：{r['what_worked']}")
        if r.get("what_failed"):
            lines.append(f"  效果差：{r['what_failed']}")
        if r.get("student_reaction"):
            lines.append(f"  学生反应：{r['student_reaction']}")
        if r.get("next_adjustment"):
            lines.append(f"  调整建议：{r['next_adjustment']}")

    return "\n".join(lines)


def list_reflections(key: str) -> List[Dict[str, Any]]:
    """列出指定教案的所有反思。

    Args:
        key: 缓存 key

    Returns:
        反思列表
    """
    index = _load_index()
    entry = index.get(key)
    if not entry:
        return []

    path = PLANS_DIR / entry["file"]
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("reflections", [])
    except (json.JSONDecodeError, IOError):
        return []
