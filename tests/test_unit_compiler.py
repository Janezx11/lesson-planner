"""compiler.unit_compiler 单元计划模块测试"""

import pytest
from unittest.mock import MagicMock
from compiler.unit_compiler import (
    generate_unit_plan,
    build_lesson_context,
    validate_unit_coherence,
    _create_default_unit_plan,
)
from models.runtime import UnitPlan, LessonOutline, TeacherRuntimePlan, ClassroomSection


class TestUnitPlanModel:
    """UnitPlan 模型测试"""

    def test_create_unit_plan(self):
        plan = UnitPlan(
            unit_title="二次函数单元",
            topic="二次函数",
            grade="高二",
            total_lessons=3,
            unit_objectives=["掌握二次函数"],
            lessons=[
                LessonOutline(lesson_number=1, title="概念", core_content="定义", objectives=["理解定义"]),
                LessonOutline(lesson_number=2, title="图像", core_content="性质", objectives=["掌握图像"]),
                LessonOutline(lesson_number=3, title="应用", core_content="综合", objectives=["解决问题"]),
            ],
        )
        assert plan.total_lessons == 3
        assert len(plan.lessons) == 3
        assert plan.lessons[0].title == "概念"

    def test_lesson_outline_defaults(self):
        lo = LessonOutline(lesson_number=1, title="测试", core_content="内容", objectives=["目标"])
        assert lo.duration == "45分钟"
        assert lo.prerequisites == ""


class TestBuildLessonContext:
    """课时上下文构建测试"""

    def _make_unit_plan(self):
        return UnitPlan(
            unit_title="二次函数单元",
            topic="二次函数",
            grade="高二",
            total_lessons=3,
            unit_objectives=["掌握二次函数"],
            progression_logic="从概念到应用",
            lessons=[
                LessonOutline(lesson_number=1, title="概念", core_content="定义", objectives=["理解定义"]),
                LessonOutline(lesson_number=2, title="图像", core_content="性质", objectives=["掌握图像"], prerequisites="概念课的定义"),
                LessonOutline(lesson_number=3, title="应用", core_content="综合", objectives=["解决问题"], prerequisites="图像课的性质"),
            ],
        )

    def test_first_lesson_no_previous(self):
        unit = self._make_unit_plan()
        context = build_lesson_context(unit, unit.lessons[0])
        assert "第 1/3 课时" in context
        assert "二次函数" in context
        assert "上一课时" not in context

    def test_second_lesson_with_previous(self):
        unit = self._make_unit_plan()
        context = build_lesson_context(unit, unit.lessons[1], previous_summary="学习了二次函数的定义")
        assert "第 2/3 课时" in context
        assert "学习了二次函数的定义" in context
        assert "自然衔接" in context

    def test_contains_unit_objectives(self):
        unit = self._make_unit_plan()
        context = build_lesson_context(unit, unit.lessons[0])
        assert "掌握二次函数" in context

    def test_contains_progression_logic(self):
        unit = self._make_unit_plan()
        context = build_lesson_context(unit, unit.lessons[0])
        assert "从概念到应用" in context


class TestValidateUnitCoherence:
    """单元连贯性校验测试"""

    def _make_lessons(self):
        return [
            TeacherRuntimePlan(
                topic="概念", grade="高二",
                teaching_objectives=["理解定义", "掌握公式"],
                sections=[
                    ClassroomSection(title="导入", teacher_activity="讲", student_activity="听", duration_minutes=10),
                    ClassroomSection(title="练习", teacher_activity="看", student_activity="做", duration_minutes=20),
                ],
                summary="学习了定义",
            ),
            TeacherRuntimePlan(
                topic="图像", grade="高二",
                teaching_objectives=["掌握图像", "理解性质"],
                sections=[
                    ClassroomSection(title="导入", teacher_activity="讲", student_activity="听", duration_minutes=10),
                    ClassroomSection(title="练习", teacher_activity="看", student_activity="做", duration_minutes=20),
                ],
                summary="学习了图像",
            ),
        ]

    def test_no_issues_for_coherent_lessons(self):
        lessons = self._make_lessons()
        unit = UnitPlan(
            unit_title="测试", topic="测试", grade="高二", total_lessons=2,
            lessons=[
                LessonOutline(lesson_number=1, title="A", core_content="a", objectives=["o1"]),
                LessonOutline(lesson_number=2, title="B", core_content="b", objectives=["o2"]),
            ],
        )
        issues = validate_unit_coherence(unit, lessons)
        assert len(issues) == 0

    def test_detects_overlapping_objectives(self):
        lessons = self._make_lessons()
        # 故意让两个课时有相同目标
        lessons[0].teaching_objectives = ["理解定义", "掌握图像"]
        lessons[1].teaching_objectives = ["掌握图像", "理解性质"]
        unit = UnitPlan(
            unit_title="测试", topic="测试", grade="高二", total_lessons=2,
            lessons=[
                LessonOutline(lesson_number=1, title="A", core_content="a"),
                LessonOutline(lesson_number=2, title="B", core_content="b"),
            ],
        )
        issues = validate_unit_coherence(unit, lessons)
        assert any("重叠" in i for i in issues)

    def test_detects_lesson_count_mismatch(self):
        lessons = self._make_lessons()
        unit = UnitPlan(
            unit_title="测试", topic="测试", grade="高二", total_lessons=3,
            lessons=[
                LessonOutline(lesson_number=1, title="A", core_content="a"),
                LessonOutline(lesson_number=2, title="B", core_content="b"),
                LessonOutline(lesson_number=3, title="C", core_content="c"),
            ],
        )
        issues = validate_unit_coherence(unit, lessons)
        assert any("课时数不匹配" in i for i in issues)


class TestGenerateUnitPlan:
    """单元计划生成测试"""

    def test_default_plan_has_correct_lessons(self):
        plan = _create_default_unit_plan("二次函数", "高二", 3, "45分钟")
        assert plan.total_lessons == 3
        assert len(plan.lessons) == 3
        assert plan.lessons[0].lesson_number == 1
        assert plan.lessons[2].lesson_number == 3

    def test_default_plan_has_prerequisites(self):
        plan = _create_default_unit_plan("二次函数", "高二", 3, "45分钟")
        assert plan.lessons[0].prerequisites == ""  # 第一课时无前置
        assert "第1课时" in plan.lessons[1].prerequisites  # 第二课时依赖第一课时

    def test_mock_llm_returns_unit_plan(self):
        mock_client = MagicMock()
        unit = UnitPlan(
            unit_title="测试单元", topic="测试", grade="高二", total_lessons=2,
            unit_objectives=["目标"],
            lessons=[
                LessonOutline(lesson_number=1, title="A", core_content="a", objectives=["o1"]),
                LessonOutline(lesson_number=2, title="B", core_content="b", objectives=["o2"]),
            ],
        )
        mock_client.generate_structured_output_v2.return_value = unit

        result = generate_unit_plan("测试", "高二", 2, "45分钟", "普通", mock_client)
        assert result.total_lessons == 2
        assert result.unit_title == "测试单元"
