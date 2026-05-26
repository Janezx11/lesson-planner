"""
Tests for graph state and workflow builder.
"""

import pytest
from graph.state import TeachingState, NodeNames, WorkflowEdges, create_initial_state


class TestTeachingState:
    def test_create_initial_state(self):
        state = create_initial_state("二次函数", "高二")
        assert state.topic == "二次函数"
        assert state.grade == "高二"
        assert state.provider == "claude"
        assert state.plan == {}
        assert state.runtime == {}
        assert state.final_output == {}
        assert state.error_count == 0
        assert state.warnings == []

    def test_state_partial_update(self):
        state = create_initial_state("test", "test")
        state_dict = state.model_dump()
        state_dict["plan"] = {"lesson_overview": "test"}
        updated = TeachingState.model_validate(state_dict)
        assert updated.plan["lesson_overview"] == "test"
        assert updated.topic == "test"

    def test_state_with_warnings(self):
        state = create_initial_state("test", "test")
        state_dict = state.model_dump()
        state_dict["warnings"] = ["[planner_node] fallback used"]
        updated = TeachingState.model_validate(state_dict)
        assert len(updated.warnings) == 1


class TestNodeNames:
    def test_node_names(self):
        assert NodeNames.COMPILER == "compiler_node"
        assert NodeNames.RENDERER == "renderer_node"
        assert not hasattr(NodeNames, 'FORMATTER')


class TestWorkflowBuilder:
    def test_build_workflow(self):
        from graph.builder import WorkflowBuilder
        builder = WorkflowBuilder(default_provider="claude")
        graph = builder.build_workflow()
        assert graph is not None

    def test_workflow_has_correct_nodes(self):
        from graph.builder import WorkflowBuilder
        builder = WorkflowBuilder(default_provider="claude")
        builder.build_workflow()
        nodes = list(builder.workflow.nodes.keys())
        for name in ["planner_node", "knowledge_node", "design_node",
                      "content_node", "compiler_node", "renderer_node"]:
            assert name in nodes
        assert "formatter_node" not in nodes
