"""compiler.pedagogical_compiler 质量模块测试"""

import pytest
from unittest.mock import MagicMock
from compiler.pedagogical_compiler import (
    _scrub_cognitive_terms,
    _scrub_plan_recursively,
    score_runtime_plan,
    validate_runtime_plan,
    improve_existing_plan,
    regenerate_section,
    ChangeSpec,
    ModifySectionChange,
    AddSectionChange,
    _apply_change_spec,
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


class TestApplyChangeSpec:
    """ChangeSpec 程序合并测试"""

    def _make_plan(self):
        return TeacherRuntimePlan(
            topic="二次函数",
            grade="高二",
            teaching_objectives=["理解二次函数"],
            sections=[
                ClassroomSection(title="导入新课", teacher_activity="展示案例", student_activity="观察", duration_minutes=10),
                ClassroomSection(title="合作探究", teacher_activity="组织讨论", student_activity="分组讨论", duration_minutes=20),
                ClassroomSection(title="巩固练习", teacher_activity="讲解例题", student_activity="独立练习", duration_minutes=15),
            ],
            homework=[HomeworkTask(type="必做", content="课后习题", purpose="巩固")],
            summary="学习了二次函数",
        )

    def test_modify_section(self):
        plan = self._make_plan()
        spec = ChangeSpec(
            modify_sections=[ModifySectionChange(section_index=0, title="悬念导入", duration_minutes=8)],
        )
        result = _apply_change_spec(plan, spec)
        assert result.sections[0].title == "悬念导入"
        assert result.sections[0].duration_minutes == 8
        # 其他环节不变
        assert result.sections[1].title == "合作探究"

    def test_add_section(self):
        plan = self._make_plan()
        spec = ChangeSpec(
            add_sections=[AddSectionChange(after_index=1, title="小组实验", teacher_activity="组织实验", student_activity="动手操作", duration_minutes=15)],
        )
        result = _apply_change_spec(plan, spec)
        assert len(result.sections) == 4
        assert result.sections[2].title == "小组实验"
        # 原来的第 3 个环节变成第 4 个
        assert result.sections[3].title == "巩固练习"

    def test_update_objectives(self):
        plan = self._make_plan()
        spec = ChangeSpec(update_objectives=["新目标A", "新目标B"])
        result = _apply_change_spec(plan, spec)
        assert result.teaching_objectives == ["新目标A", "新目标B"]

    def test_update_summary(self):
        plan = self._make_plan()
        spec = ChangeSpec(update_summary="新的课堂小结")
        result = _apply_change_spec(plan, spec)
        assert result.summary == "新的课堂小结"

    def test_empty_spec_preserves_plan(self):
        plan = self._make_plan()
        spec = ChangeSpec()  # 什么都不改
        result = _apply_change_spec(plan, spec)
        assert result.summary == plan.summary
        assert len(result.sections) == len(plan.sections)
        assert result.teaching_objectives == plan.teaching_objectives

    def test_cleans_cognitive_terms(self):
        plan = self._make_plan()
        spec = ChangeSpec(update_summary="通过认知冲突激发兴趣")
        result = _apply_change_spec(plan, spec)
        assert "认知" not in result.summary


class TestImproveExistingPlan:
    """教案改进测试（Change Spec 方案）"""

    def _make_plan(self):
        return TeacherRuntimePlan(
            topic="二次函数",
            grade="高二",
            teaching_objectives=["理解二次函数"],
            sections=[
                ClassroomSection(title="导入新课", teacher_activity="展示案例", student_activity="观察", duration_minutes=10),
                ClassroomSection(title="合作探究", teacher_activity="组织讨论", student_activity="分组讨论", duration_minutes=20),
                ClassroomSection(title="巩固练习", teacher_activity="讲解例题", student_activity="独立练习", duration_minutes=15),
            ],
            homework=[HomeworkTask(type="必做", content="课后习题", purpose="巩固")],
            summary="学习了二次函数",
        )

    def test_improve_applies_change_spec(self):
        original = self._make_plan()
        change_spec = ChangeSpec(
            update_summary="改进后的课堂小结",
            reason="优化小结内容",
        )
        mock_client = MagicMock()
        mock_client.generate_structured_output_v2.return_value = change_spec

        result = improve_existing_plan(original, "优化小结", "二次函数", "高二", mock_client)

        assert isinstance(result, TeacherRuntimePlan)
        assert result.summary == "改进后的课堂小结"
        # 未改动的字段保持不变
        assert result.sections[0].title == "导入新课"
        assert result.topic == "二次函数"

    def test_improve_preserves_untouched_fields(self):
        original = self._make_plan()
        change_spec = ChangeSpec(
            modify_sections=[ModifySectionChange(section_index=1, duration_minutes=25)],
            reason="延长讨论时间",
        )
        mock_client = MagicMock()
        mock_client.generate_structured_output_v2.return_value = change_spec

        result = improve_existing_plan(original, "延长讨论", "二次函数", "高二", mock_client)

        assert result.sections[1].duration_minutes == 25
        # 其他字段不变
        assert result.sections[0].title == "导入新课"
        assert result.sections[2].title == "巩固练习"
        assert result.summary == "学习了二次函数"
        assert result.homework[0].content == "课后习题"

    def test_improve_returns_original_on_llm_failure(self):
        original = self._make_plan()
        mock_client = MagicMock()
        mock_client.generate_structured_output_v2.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            improve_existing_plan(original, "优化", "二次函数", "高二", mock_client)

    def test_improve_passes_instructions_to_llm(self):
        original = self._make_plan()
        change_spec = ChangeSpec(reason="无改动")
        mock_client = MagicMock()
        mock_client.generate_structured_output_v2.return_value = change_spec

        improve_existing_plan(original, "增加小组讨论", "二次函数", "高二", mock_client)

        call_args = mock_client.generate_structured_output_v2.call_args
        prompt = call_args.kwargs.get("prompt", call_args[1].get("prompt", ""))
        assert "增加小组讨论" in prompt


class TestRegenerateSection:
    """局部重新生成测试"""

    def _make_plan(self):
        return TeacherRuntimePlan(
            topic="二次函数",
            grade="高二",
            teaching_objectives=["理解二次函数"],
            sections=[
                ClassroomSection(title="导入新课", teacher_activity="展示案例", student_activity="观察", duration_minutes=10),
                ClassroomSection(title="合作探究", teacher_activity="组织讨论", student_activity="分组讨论", duration_minutes=20),
                ClassroomSection(title="巩固练习", teacher_activity="讲解例题", student_activity="独立练习", duration_minutes=15),
            ],
            homework=[HomeworkTask(type="必做", content="课后习题", purpose="巩固")],
            summary="学习了二次函数",
        )

    def test_regenerate_replaces_target_section(self):
        original = self._make_plan()
        new_section = ClassroomSection(
            title="小组探究",
            teacher_activity="组织小组实验",
            student_activity="动手操作并记录",
            duration_minutes=25,
        )
        mock_client = MagicMock()
        mock_client.generate_structured_output_v2.return_value = new_section

        result = regenerate_section(original, 1, "增加动手环节", mock_client)

        assert result.sections[1].title == "小组探究"
        assert result.sections[1].duration_minutes == 25

    def test_regenerate_preserves_other_sections(self):
        original = self._make_plan()
        new_section = ClassroomSection(title="新环节", teacher_activity="新活动", student_activity="新学生活动", duration_minutes=10)
        mock_client = MagicMock()
        mock_client.generate_structured_output_v2.return_value = new_section

        result = regenerate_section(original, 1, "改", mock_client)

        # 其他环节保持不变
        assert result.sections[0].title == "导入新课"
        assert result.sections[2].title == "巩固练习"
        assert result.summary == original.summary

    def test_regenerate_invalid_index_returns_original(self):
        original = self._make_plan()
        mock_client = MagicMock()

        result = regenerate_section(original, 5, "改", mock_client)
        assert result.sections[0].title == "导入新课"
        mock_client.generate_structured_output_v2.assert_not_called()

    def test_regenerate_negative_index_returns_original(self):
        original = self._make_plan()
        mock_client = MagicMock()

        result = regenerate_section(original, -1, "改", mock_client)
        assert result.sections[0].title == "导入新课"
        mock_client.generate_structured_output_v2.assert_not_called()

    def test_regenerate_cleans_cognitive_terms(self):
        original = self._make_plan()
        new_section = ClassroomSection(
            title="认知冲突导入",
            teacher_activity="激发认知冲突",
            student_activity="产生认知冲突",
            duration_minutes=10,
        )
        mock_client = MagicMock()
        mock_client.generate_structured_output_v2.return_value = new_section

        result = regenerate_section(original, 0, "改", mock_client)

        # 认知术语应被清除
        assert "认知" not in result.sections[0].title
        assert "认知" not in result.sections[0].teacher_activity
