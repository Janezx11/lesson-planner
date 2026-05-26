"""
Tests for compiler and renderer components.
"""

import pytest
from compiler.prompt_builder import build_compiler_prompt, MAX_PROMPT_CHARS
from compiler.pedagogical_compiler import validate_runtime_plan, _create_default_runtime_plan
from renderers.markdown_renderer import render_markdown
from models.runtime import TeacherRuntimePlan, ClassroomSection, BlackboardDesign


# ============================================================
# Prompt Builder
# ============================================================

class TestPromptBuilder:
    def test_basic_prompt(self):
        prompt = build_compiler_prompt(
            cognitive_flow={"lesson_overview": "test", "stages": []},
            knowledge_structure=None,
            interaction_design=None,
            practice_design=None,
            misconception_model=None,
            blackboard_design=None,
            homework=None,
            topic="二次函数",
            grade="高二",
        )
        assert "二次函数" in prompt
        assert "高二" in prompt
        assert "认知推进路线" in prompt

    def test_prompt_with_all_sections(self):
        prompt = build_compiler_prompt(
            cognitive_flow={"lesson_overview": "test", "stages": [{"stage_name": "s1"}]},
            knowledge_structure={"core_concepts": [{"concept": "c1"}]},
            interaction_design={"interaction_points": []},
            practice_design={"basic": []},
            misconception_model={"items": []},
            blackboard_design={"layout": "center"},
            homework=[{"type": "必做", "content": "hw1"}],
            topic="test",
            grade="test",
        )
        assert "知识结构分析" in prompt
        assert "互动设计策略" in prompt
        assert "练习题设计" in prompt
        assert "作业设计" in prompt

    def test_empty_cognitive_flow_handled(self):
        """Empty cognitive_flow should not crash."""
        prompt = build_compiler_prompt(
            cognitive_flow={},
            knowledge_structure=None,
            interaction_design=None,
            practice_design=None,
            misconception_model=None,
            blackboard_design=None,
            homework=None,
            topic="test",
            grade="test",
        )
        assert "test" in prompt

    def test_prompt_size_limit(self):
        """Prompt should be truncated if too large."""
        # Create a very large cognitive flow
        large_flow = {
            "lesson_overview": "x" * 10000,
            "stages": [{"stage_name": f"stage_{i}", "data": "y" * 1000} for i in range(20)],
        }
        prompt = build_compiler_prompt(
            cognitive_flow=large_flow,
            knowledge_structure={"core_concepts": [{"concept": "z" * 5000}]},
            interaction_design={"data": "w" * 5000},
            practice_design=None,
            misconception_model=None,
            blackboard_design=None,
            homework=None,
            topic="test",
            grade="test",
        )
        # Should not exceed limit by much (some overhead for section headers)
        assert len(prompt) <= MAX_PROMPT_CHARS + 500  # small margin for headers


# ============================================================
# Pedagogical Compiler
# ============================================================

class TestPedagogicalCompiler:
    def test_validate_runtime_plan_good(self):
        plan = TeacherRuntimePlan(
            topic="test",
            grade="test",
            teaching_objectives=["学生能够理解X"],
            sections=[
                ClassroomSection(title="导入", teacher_activity="do", student_activity="do"),
                ClassroomSection(title="练习", teacher_activity="do", student_activity="do"),
            ],
        )
        issues = validate_runtime_plan(plan)
        assert issues == []

    def test_validate_runtime_plan_no_objectives(self):
        plan = TeacherRuntimePlan(topic="test", grade="test", sections=[
            ClassroomSection(title="s1", teacher_activity="do", student_activity="do"),
            ClassroomSection(title="s2", teacher_activity="do", student_activity="do"),
        ])
        issues = validate_runtime_plan(plan)
        assert any("教学目标" in i for i in issues)

    def test_validate_runtime_plan_too_few_sections(self):
        plan = TeacherRuntimePlan(
            topic="test", grade="test",
            teaching_objectives=["obj"],
            sections=[ClassroomSection(title="s1", teacher_activity="do", student_activity="do")],
        )
        issues = validate_runtime_plan(plan)
        assert any("教学环节" in i for i in issues)

    def test_validate_detects_cognitive_leakage(self):
        """Should detect if cognitive terms leaked into runtime plan."""
        plan = TeacherRuntimePlan(
            topic="test", grade="test",
            teaching_objectives=["认知冲突的目标"],
            sections=[
                ClassroomSection(title="s1", teacher_activity="do", student_activity="do"),
                ClassroomSection(title="s2", teacher_activity="do", student_activity="do"),
            ],
        )
        issues = validate_runtime_plan(plan)
        assert any("认知术语" in i or "认知" in i for i in issues)

    def test_default_runtime_plan(self):
        plan = _create_default_runtime_plan("二次函数", "高二")
        assert plan.topic == "二次函数"
        assert plan.grade == "高二"
        assert len(plan.sections) >= 2
        assert len(plan.homework) >= 1


# ============================================================
# Markdown Renderer
# ============================================================

class TestMarkdownRenderer:
    def test_basic_render(self):
        plan = TeacherRuntimePlan(topic="二次函数", grade="高二")
        md = render_markdown(plan)
        assert "# 二次函数" in md
        assert "高二" in md

    def test_render_with_sections(self):
        plan = TeacherRuntimePlan(
            topic="test", grade="test",
            teaching_objectives=["目标1"],
            sections=[
                ClassroomSection(title="导入", teacher_activity="展示", student_activity="观察", duration_minutes=10),
            ],
        )
        md = render_markdown(plan)
        assert "导入" in md
        assert "展示" in md
        assert "10分钟" in md

    def test_render_with_practice(self):
        from models.runtime import PracticeQuestion
        plan = TeacherRuntimePlan(
            topic="test", grade="test",
            practice_questions=[
                PracticeQuestion(question="Q1?", answer="A1", difficulty="基础"),
            ],
        )
        md = render_markdown(plan)
        assert "Q1?" in md
        assert "A1" in md

    def test_render_with_homework(self):
        from models.runtime import HomeworkTask
        plan = TeacherRuntimePlan(
            topic="test", grade="test",
            homework=[HomeworkTask(type="必做", content="练习1-3")],
        )
        md = render_markdown(plan)
        assert "必做" in md
        assert "练习1-3" in md

    def test_render_with_blackboard(self):
        plan = TeacherRuntimePlan(
            topic="test", grade="test",
            blackboard=BlackboardDesign(layout="三区", main_content=["核心内容"]),
        )
        md = render_markdown(plan)
        assert "三区" in md
        assert "核心内容" in md

    def test_render_empty_plan(self):
        plan = TeacherRuntimePlan(topic="", grade="")
        md = render_markdown(plan)
        assert isinstance(md, str)
        assert len(md) > 0
