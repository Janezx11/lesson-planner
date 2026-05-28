"""缓存模块测试"""

import pytest
import shutil
from pathlib import Path
from cache import (
    get_cache_key,
    get_cached,
    set_cached,
    clear_cache,
    cache_stats,
    list_cached,
    delete_cached,
    CACHE_DIR,
)


@pytest.fixture(autouse=True)
def clean_cache():
    """每个测试前后清理缓存目录"""
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
    yield
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)


class TestCacheKey:
    """缓存 key 生成测试"""

    def test_consistent_key(self):
        k1 = get_cache_key("二次函数", "高二", "mimo")
        k2 = get_cache_key("二次函数", "高二", "mimo")
        assert k1 == k2

    def test_different_inputs_different_keys(self):
        k1 = get_cache_key("二次函数", "高二", "mimo")
        k2 = get_cache_key("一次函数", "高二", "mimo")
        k3 = get_cache_key("二次函数", "高一", "mimo")
        assert k1 != k2
        assert k1 != k3

    def test_case_insensitive(self):
        k1 = get_cache_key("二次函数", "高二", "Mimo")
        k2 = get_cache_key("二次函数", "高二", "mimo")
        assert k1 == k2

    def test_whitespace_trimmed(self):
        k1 = get_cache_key(" 二次函数 ", " 高二 ", " mimo ")
        k2 = get_cache_key("二次函数", "高二", "mimo")
        assert k1 == k2

    def test_key_length(self):
        k = get_cache_key("任意主题", "任意年级", "任意提供商")
        assert len(k) == 16


class TestCacheReadWrite:
    """缓存读写测试"""

    def test_write_and_read(self):
        data = {"metadata": {"topic": "测试"}, "result": [1, 2, 3]}
        key = get_cache_key("测试", "高一", "mimo")

        assert set_cached(key, data) is True
        cached = get_cached(key)
        assert cached is not None
        assert cached["metadata"]["topic"] == "测试"
        assert cached["result"] == [1, 2, 3]

    def test_miss_returns_none(self):
        result = get_cached("nonexistent_key")
        assert result is None

    def test_error_not_cached(self):
        data = {"error": "something failed"}
        key = get_cache_key("失败主题", "高一", "mimo")

        assert set_cached(key, data) is False
        assert get_cached(key) is None

    def test_overwrite_existing(self):
        key = get_cache_key("主题", "年级", "provider")

        set_cached(key, {"version": 1})
        set_cached(key, {"version": 2})

        cached = get_cached(key)
        assert cached["version"] == 2


class TestCacheClear:
    """缓存清除测试"""

    def test_clear_returns_count(self):
        set_cached("key1", {"a": 1})
        set_cached("key2", {"b": 2})
        set_cached("key3", {"c": 3})

        count = clear_cache()
        assert count == 3
        assert get_cached("key1") is None

    def test_clear_empty_cache(self):
        count = clear_cache()
        assert count == 0


class TestCacheStats:
    """缓存统计测试"""

    def test_stats_empty(self):
        stats = cache_stats()
        assert stats["count"] == 0
        assert stats["total_size_kb"] == 0

    def test_stats_with_files(self):
        set_cached("key1", {"a": "x" * 1000})
        set_cached("key2", {"b": "y" * 1000})

        stats = cache_stats()
        assert stats["count"] == 2
        assert stats["total_size_kb"] > 0


class TestListCached:
    """list_cached 测试"""

    def test_empty_list(self):
        assert list_cached() == []

    def test_list_returns_entries(self):
        set_cached("k1", {"metadata": {"topic": "二次函数", "grade": "高二", "llm_provider": "mimo", "generated_at": "2026-01-01"}})
        set_cached("k2", {"metadata": {"topic": "牛顿定律", "grade": "高一", "llm_provider": "mimo", "generated_at": "2026-01-02"}})

        entries = list_cached()
        assert len(entries) == 2
        topics = [e["topic"] for e in entries]
        assert "二次函数" in topics
        assert "牛顿定律" in topics

    def test_entry_has_required_fields(self):
        set_cached("k1", {"metadata": {"topic": "测试", "grade": "高一", "llm_provider": "mimo", "generated_at": "2026-01-01"}})

        entries = list_cached()
        entry = entries[0]
        assert "key" in entry
        assert "topic" in entry
        assert "grade" in entry
        assert "provider" in entry
        assert "generated_at" in entry
        assert "size_kb" in entry

    def test_sorted_by_time_newest_first(self):
        import time
        set_cached("k1", {"metadata": {"topic": "A", "grade": "高一", "llm_provider": "mimo", "generated_at": "2026-01-01"}})
        time.sleep(0.05)
        set_cached("k2", {"metadata": {"topic": "B", "grade": "高一", "llm_provider": "mimo", "generated_at": "2026-01-02"}})

        entries = list_cached()
        assert entries[0]["topic"] == "B"  # 最新的在前


class TestDeleteCached:
    """delete_cached 测试"""

    def test_delete_existing(self):
        set_cached("k1", {"a": 1})
        assert delete_cached("k1") is True
        assert get_cached("k1") is None

    def test_delete_nonexistent(self):
        assert delete_cached("no_such_key") is False

    def test_delete_one_keeps_others(self):
        set_cached("k1", {"a": 1})
        set_cached("k2", {"b": 2})

        delete_cached("k1")
        assert get_cached("k1") is None
        assert get_cached("k2") is not None
