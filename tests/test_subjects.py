"""学科模板系统测试"""

import pytest
from models.subjects import (
    detect_subject,
    get_subject_guidance,
    format_subject_guidance,
    SUBJECTS,
)


class TestDetectSubject:
    """学科自动检测测试"""

    def test_detect_math(self):
        assert detect_subject("二次函数") == "数学"
        assert detect_subject("三角形的面积") == "数学"
        assert detect_subject("导数的应用") == "数学"

    def test_detect_physics(self):
        assert detect_subject("牛顿第二定律") == "物理"
        assert detect_subject("电磁感应") == "物理"
        assert detect_subject("加速度") == "物理"

    def test_detect_chemistry(self):
        assert detect_subject("化学方程式配平") == "化学"
        assert detect_subject("氧化还原反应") == "化学"

    def test_detect_biology(self):
        assert detect_subject("光合作用") == "生物"
        assert detect_subject("细胞的结构") == "生物"
        assert detect_subject("DNA的复制") == "生物"

    def test_detect_chinese(self):
        assert detect_subject("古诗词鉴赏") == "语文"
        assert detect_subject("议论文写作") == "语文"

    def test_detect_english(self):
        assert detect_subject("现在进行时语法") == "英语"
        assert detect_subject("虚拟语气") == "英语"

    def test_detect_history(self):
        assert detect_subject("辛亥革命") == "历史"
        assert detect_subject("朝代变迁") == "历史"

    def test_detect_geography(self):
        assert detect_subject("气候类型") == "地理"
        assert detect_subject("洋流分布") == "地理"

    def test_detect_it(self):
        assert detect_subject("编程基础") == "信息技术"
        assert detect_subject("算法分析") == "信息技术"
        assert detect_subject("网络分层协议") == "信息技术"

    def test_detect_politics(self):
        assert detect_subject("市场经济") == "政治"

    def test_unknown_returns_none(self):
        assert detect_subject("未知主题XYZ") is None
        assert detect_subject("吃饭睡觉") is None


class TestGetSubjectGuidance:
    """获取学科指导测试"""

    def test_get_math_guidance(self):
        g = get_subject_guidance("数学")
        assert g is not None
        assert g.name == "数学"
        assert "认知冲突" in g.preferred_stages
        assert len(g.objective_verbs) > 0

    def test_get_unknown_returns_none(self):
        assert get_subject_guidance("不存在的学科") is None
        assert get_subject_guidance(None) is None

    def test_all_subjects_have_guidance(self):
        for name in SUBJECTS:
            g = get_subject_guidance(name)
            assert g is not None, f"学科 {name} 缺少指导"
            assert g.display_name, f"学科 {name} 缺少 display_name"


class TestFormatSubjectGuidance:
    """格式化测试"""

    def test_format_math(self):
        g = get_subject_guidance("数学")
        text = format_subject_guidance(g)
        assert "数学" in text
        assert "认知冲突" in text
        assert "推荐认知阶段" in text

    def test_format_none_returns_empty(self):
        assert format_subject_guidance(None) == ""

    def test_format_includes_all_sections(self):
        g = get_subject_guidance("物理")
        text = format_subject_guidance(g)
        assert "推荐认知阶段" in text
        assert "推荐教学策略" in text
        assert "知识结构" in text or "重点关注" in text
        assert "练习题" in text
