"""
Tests for exporters (DOCX, Markdown).
"""

import os
import pytest
from pathlib import Path
from models.runtime import TeacherRuntimePlan, ClassroomSection, HomeworkTask, BlackboardDesign
from exporters import export_to_docx, export_to_markdown


@pytest.fixture
def sample_plan():
    return TeacherRuntimePlan(
        topic="二次函数",
        grade="高二",
        duration="45分钟",
        teaching_methods=["讲授法"],
        teaching_objectives=["理解二次函数的图像"],
        key_points=["开口方向"],
        difficult_points=["顶点坐标"],
        sections=[
            ClassroomSection(
                title="导入新课",
                teacher_activity="展示抛物线图片",
                student_activity="观察并讨论",
                duration_minutes=10,
                teaching_intent="激发兴趣",
            ),
            ClassroomSection(
                title="合作探究",
                teacher_activity="引导学生画图",
                student_activity="分组画图并讨论",
                interaction_method="小组讨论",
                duration_minutes=20,
            ),
        ],
        homework=[
            HomeworkTask(type="必做", content="练习1-3", purpose="巩固"),
        ],
        blackboard=BlackboardDesign(
            layout="三区布局",
            main_content=["二次函数 y=ax^2+bx+c"],
        ),
        summary="本节课学习了二次函数的基本性质",
    )


@pytest.fixture
def output_dir(tmp_path):
    return str(tmp_path)


class TestDocxExporter:
    def test_export_creates_file(self, sample_plan, output_dir):
        path = os.path.join(output_dir, "test.docx")
        result = export_to_docx(sample_plan, path)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    def test_export_returns_path(self, sample_plan, output_dir):
        path = os.path.join(output_dir, "test.docx")
        result = export_to_docx(sample_plan, path)
        assert result == path

    def test_export_minimal_plan(self, output_dir):
        plan = TeacherRuntimePlan(topic="test", grade="test")
        path = os.path.join(output_dir, "minimal.docx")
        result = export_to_docx(plan, path)
        assert os.path.exists(result)

    def test_export_with_all_fields(self, sample_plan, output_dir):
        """Full plan with all fields should export without error."""
        from models.runtime import ClassroomInteraction, PracticeQuestion
        sample_plan.interactions = [
            ClassroomInteraction(
                trigger="讲到开口方向时",
                teacher_question="抛物线开口朝哪？",
                expected_responses=["朝上"],
            ),
        ]
        sample_plan.practice_questions = [
            PracticeQuestion(question="y=x^2 开口？", answer="朝上", difficulty="基础"),
        ]
        path = os.path.join(output_dir, "full.docx")
        result = export_to_docx(sample_plan, path)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 1000  # Should be substantial


class TestMarkdownExporter:
    def test_export_creates_file(self, sample_plan, output_dir):
        path = os.path.join(output_dir, "test.md")
        result = export_to_markdown(sample_plan, path)
        assert os.path.exists(result)

    def test_export_content(self, sample_plan, output_dir):
        path = os.path.join(output_dir, "test.md")
        export_to_markdown(sample_plan, path)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "二次函数" in content
        assert "导入新课" in content
        assert "合作探究" in content
