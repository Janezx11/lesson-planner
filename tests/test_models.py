"""
Tests for Pydantic models - Cognitive IR and Runtime.
"""

import pytest
from models.cognitive import (
    CognitiveFlow, CognitiveStage, StudentAnalysis, TeachingObjectives,
    KnowledgeStructure, CoreConcept, CommonMistake,
    InteractionDesign, InteractionPoint, QuestionStrategy, TeacherBehavior, StudentBehavior,
    PracticeDesign, PracticeQuestion as CognitivePracticeQuestion,
    MisconceptionModel, MisconceptionItem,
)
from models.runtime import (
    TeacherRuntimePlan, ClassroomSection, ClassroomInteraction,
    HomeworkTask, BlackboardDesign, PracticeQuestion,
)
from models.content import (
    ContentOutput, ContentPracticeDesign, ContentPracticeQuestion,
    ContentBlackboardDesign, HomeworkItem, ContentMistake,
)


# ============================================================
# Cognitive IR Models
# ============================================================

class TestCognitiveFlow:
    def test_minimal(self):
        flow = CognitiveFlow(lesson_overview="test overview")
        assert flow.lesson_overview == "test overview"
        assert flow.stages == []
        assert flow.lesson_duration == "45分钟"

    def test_with_stages(self):
        stage = CognitiveStage(
            stage_name="认知冲突：为什么需要学习",
            cognitive_state="学生认为很简单",
            cognitive_goal="激发兴趣",
            teaching_strategy="认知冲突",
            duration="10分钟",
            teacher_activity=["播放视频"],
            student_activity=["观看视频"],
            expected_cognitive_change="从简单到复杂",
        )
        flow = CognitiveFlow(
            lesson_overview="test",
            stages=[stage],
        )
        assert len(flow.stages) == 1
        assert flow.stages[0].stage_name == "认知冲突：为什么需要学习"

    def test_json_roundtrip(self):
        flow = CognitiveFlow(lesson_overview="test", stages=[
            CognitiveStage(stage_name="test stage", teaching_strategy="test")
        ])
        d = flow.model_dump()
        restored = CognitiveFlow.model_validate(d)
        assert restored.lesson_overview == "test"
        assert len(restored.stages) == 1

    def test_empty_flow(self):
        flow = CognitiveFlow(lesson_overview="")
        d = flow.model_dump()
        assert "stages" in d
        assert d["stages"] == []


class TestKnowledgeStructure:
    def test_minimal(self):
        ks = KnowledgeStructure()
        assert ks.core_concepts == []
        assert ks.common_mistakes == []

    def test_with_data(self):
        ks = KnowledgeStructure(
            core_concepts=[CoreConcept(concept="分层", definition="层次结构", importance="高")],
            common_mistakes=[CommonMistake(mistake="混淆层", cause="概念不清", solution="多练习")],
        )
        assert len(ks.core_concepts) == 1
        assert ks.core_concepts[0].concept == "分层"


class TestInteractionDesign:
    def test_with_interaction_points(self):
        ip = InteractionPoint(
            stage_name="导入",
            interaction_type="提问",
            teacher_behavior=TeacherBehavior(action="提问", purpose="激发兴趣"),
            student_behavior=StudentBehavior(action="思考", cognitive_activity="分析"),
        )
        qs = QuestionStrategy(approach="递进式")
        design = InteractionDesign(interaction_points=[ip], question_strategy=qs)
        assert len(design.interaction_points) == 1


# ============================================================
# Runtime Models
# ============================================================

class TestTeacherRuntimePlan:
    def test_minimal(self):
        plan = TeacherRuntimePlan(topic="test", grade="grade 1")
        assert plan.topic == "test"
        assert plan.duration == "45分钟"
        assert plan.sections == []

    def test_full_plan(self):
        plan = TeacherRuntimePlan(
            topic="二次函数",
            grade="高二",
            duration="45分钟",
            teaching_methods=["讲授法", "讨论法"],
            teaching_objectives=["理解二次函数的图像"],
            key_points=["开口方向"],
            difficult_points=["顶点坐标"],
            sections=[
                ClassroomSection(
                    title="导入新课",
                    teacher_activity="展示抛物线图片",
                    student_activity="观察并讨论",
                    interaction_method="提问",
                    duration_minutes=10,
                    teaching_intent="激发兴趣",
                ),
            ],
            interactions=[
                ClassroomInteraction(
                    trigger="讲到开口方向时",
                    teacher_question="这条抛物线开口朝哪个方向？",
                    expected_responses=["朝上", "朝下"],
                    teacher_followup="很好，那系数a的正负呢？",
                ),
            ],
            practice_questions=[
                PracticeQuestion(
                    question="y=x^2 的开口方向？",
                    answer="朝上",
                    purpose="基础概念",
                    difficulty="基础",
                ),
            ],
            homework=[
                HomeworkTask(type="必做", content="练习1-3", purpose="巩固"),
            ],
            blackboard=BlackboardDesign(
                layout="三区",
                main_content=["二次函数"],
            ),
            summary="本节课学习了二次函数的基本性质",
        )

        assert len(plan.sections) == 1
        assert len(plan.interactions) == 1
        assert len(plan.practice_questions) == 1
        assert plan.blackboard is not None

    def test_json_roundtrip(self):
        plan = TeacherRuntimePlan(
            topic="test",
            grade="grade",
            sections=[ClassroomSection(title="s1", teacher_activity="t", student_activity="s")],
        )
        d = plan.model_dump()
        restored = TeacherRuntimePlan.model_validate(d)
        assert restored.topic == "test"
        assert len(restored.sections) == 1

    def test_no_cognitive_terms(self):
        """Runtime plan should not contain cognitive jargon."""
        plan = TeacherRuntimePlan(
            topic="test",
            grade="grade",
            teaching_objectives=["学生能够理解X"],
            sections=[ClassroomSection(title="导入新课", teacher_activity="展示案例", student_activity="观察")],
        )
        d = plan.model_dump()
        text = str(d)
        forbidden = ["认知冲突", "cognitive_state", "cognitive_goal", "misconception"]
        for term in forbidden:
            assert term not in text, f"Runtime plan contains forbidden term: {term}"


class TestClassroomSection:
    def test_minimal(self):
        section = ClassroomSection(title="test", teacher_activity="do", student_activity="do")
        assert section.duration_minutes is None
        assert section.interaction_method == ""

    def test_with_duration(self):
        section = ClassroomSection(title="test", teacher_activity="do", student_activity="do", duration_minutes=15)
        assert section.duration_minutes == 15


# ============================================================
# Content Output Models
# ============================================================

class TestContentOutput:
    def test_default(self):
        output = ContentOutput()
        assert output.practice_design is not None
        assert output.blackboard_design is not None
        assert output.homework == []

    def test_with_data(self):
        output = ContentOutput(
            practice_design=ContentPracticeDesign(
                basic=[ContentPracticeQuestion(question="Q1", answer="A1")],
            ),
            blackboard_design=ContentBlackboardDesign(layout="center"),
            homework=[HomeworkItem(type="必做", content="练习")],
        )
        assert len(output.practice_design.basic) == 1
        assert len(output.homework) == 1
