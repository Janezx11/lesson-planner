"""compiler.pedagogical_compiler 质量模块测试"""

import pytest
from compiler.pedagogical_compiler import (
    _scrub_cognitive_terms,
    _scrub_plan_recursively,
    score_runtime_plan,
    validate_runtime_plan,
)
from models.runtime import TeacherRuntimePlan, ClassroomSection, HomeworkTask, ClassroomInteraction


class TestScrubCognitiveTerms:
    """认知术语自动替换测试"""

    def test_replaces_cognitive_conflict(self):
        assert _scrub_cognitive_terms("利用认知冲突导入新课") == "利用导入新课导入新课"

    def test_replaces_cognitive_goal(self):
        assert _scrub_cognitive_terms("认知目标：学生能够理解函数") == "教学目标：学生能够理解函数"

    def test_removes_metacognition(self):
        assert _scrub_cognitive_terms("培养元认知能力") == "培养能力"

    def test_replaces_english_terms(self):
        assert _scrub_cognitive_terms("addressing misconception") == "addressing 常见错误"
        assert _scrub_cognitive_terms("using Scaffolding") == "using 学习支持"

    def test_no_change_when_clean(self):
        text = "教学目标：学生能够理解二次函数的概念"
        assert _scrub_cognitive_terms(text) == text

    def test_multiple_terms(self):
        text = "认知目标是解决认知冲突，避免misconception"
        result = _scrub_cognitive_terms(text)
        assert "认知" not in result
        assert "misconception" not in result
        assert "教学目标" in result
        assert "常见错误" in result


class TestScrubPlanRecursively:
    """递归替换测试"""

    def test_scrub_string_values(self):
        d = {"title": "认知目标：理解函数", "desc": "没有认知术语"}
        result = _scrub_plan_recursively(d)
        assert result["title"] == "教学目标：理解函数"
        assert result["desc"] == "没有认知术语"

    def test_scrub_nested_dict(self):
        d = {"section": {"title": "认知冲突导入", "note": "普通文本"}}
        result = _scrub_plan_recursively(d)
        assert "认知" not in result["section"]["title"]

    def test_scrub_list_of_strings(self):
        d = {"items": ["认知目标A", "普通B"]}
        result = _scrub_plan_recursively(d)
        assert result["items"][0] == "教学目标A"
        assert result["items"][1] == "普通B"

    def test_scrub_list_of_dicts(self):
        d = {"sections": [{"title": "认知递进讲解"}]}
        result = _scrub_plan_recursively(d)
        assert "认知" not in result["sections"][0]["title"]

    def test_preserves_non_string_values(self):
        d = {"count": 5, "flag": True, "items": [1, 2]}
        result = _scrub_plan_recursively(d)
        assert result["count"] == 5
        assert result["flag"] is True


class TestScoreRuntimePlan:
    """质量评分测试"""

    def _make_good_plan(self):
        return TeacherRuntimePlan(
            topic="二次函数",
            grade="高二",
            teaching_objectives=["学生能够理解二次函数的定义", "学生能够绘制二次函数图像"],
            sections=[
                ClassroomSection(title="导入新课", teacher_activity="展示抛物线动画", student_activity="观察并思考", duration_minutes=10),
                ClassroomSection(title="合作探究", teacher_activity="组织小组讨论", student_activity="分组讨论性质", duration_minutes=20),
                ClassroomSection(title="巩固练习", teacher_activity="讲解典型例题", student_activity="独立完成练习", duration_minutes=15),
            ],
            interactions=[
                ClassroomInteraction(trigger="导入时", teacher_question="什么是二次函数?", expected_responses=["形如y=ax^2+bx+c"], teacher_followup="很好"),
                ClassroomInteraction(trigger="练习后", teacher_question="还有其他性质吗?", expected_responses=["对称性"], teacher_followup="补充说明"),
            ],
            practice_questions=[{"question": "求顶点", "answer": "配方法", "purpose": "巩固", "difficulty": "中等"}],
            homework=[HomeworkTask(type="必做", content="课后习题", purpose="巩固")],
            summary="学习了二次函数",
        )

    def test_good_plan_scores_high(self):
        plan = self._make_good_plan()
        result = score_runtime_plan(plan)
        assert result["total"] >= 90
        assert result["grade"] == "优秀"

    def test_missing_objectives_deducts(self):
        plan = self._make_good_plan()
        plan.teaching_objectives = []
        result = score_runtime_plan(plan)
        assert result["total"] < 100
        assert any("教学目标" in d for d in result["deductions"])

    def test_cognitive_terms_deduct(self):
        plan = self._make_good_plan()
        # 直接注入认知术语到 summary
        plan_dict = plan.model_dump()
        plan_dict["summary"] = "通过认知冲突激发学生兴趣"
        plan = TeacherRuntimePlan(**plan_dict)
        result = score_runtime_plan(plan)
        assert result["scores"]["术语清洁度"] < 25

    def test_empty_plan_scores_low(self):
        plan = TeacherRuntimePlan(topic="测试", grade="高一")
        result = score_runtime_plan(plan)
        assert result["total"] < 60
        assert result["grade"] == "需改进"


class TestValidateRuntimePlan:
    """业务验证测试"""

    def test_good_plan_no_issues(self):
        plan = TeacherRuntimePlan(
            topic="测试",
            grade="高一",
            teaching_objectives=["目标1"],
            sections=[
                ClassroomSection(title="导入", teacher_activity="讲", student_activity="听", duration_minutes=10),
                ClassroomSection(title="练习", teacher_activity="看", student_activity="做", duration_minutes=20),
            ],
            summary="总结",
        )
        issues = validate_runtime_plan(plan)
        assert len(issues) == 0

    def test_missing_objectives(self):
        plan = TeacherRuntimePlan(topic="测试", grade="高一", sections=[
            ClassroomSection(title="A", teacher_activity="x", student_activity="y", duration_minutes=10),
            ClassroomSection(title="B", teacher_activity="x", student_activity="y", duration_minutes=10),
        ], summary="s")
        issues = validate_runtime_plan(plan)
        assert any("教学目标" in i for i in issues)

    def test_cognitive_term_leakage(self):
        plan = TeacherRuntimePlan(
            topic="测试", grade="高一", teaching_objectives=["目标"],
            sections=[
                ClassroomSection(title="认知冲突导入", teacher_activity="x", student_activity="y", duration_minutes=10),
                ClassroomSection(title="B", teacher_activity="x", student_activity="y", duration_minutes=10),
            ],
            summary="s",
        )
        issues = validate_runtime_plan(plan)
        assert any("认知" in i for i in issues)
