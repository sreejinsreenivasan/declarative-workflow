import pytest
from pydantic import ValidationError

from workflow_core.workflow import Node, Workflow


def test_workflow_valid_construction(linear_workflow):
    assert linear_workflow.id == "linear"
    assert linear_workflow.start == "step_a"
    assert len(linear_workflow.nodes) == 3


def test_workflow_rejects_missing_start_node():
    with pytest.raises(ValidationError, match="start node 'missing' not in nodes"):
        Workflow(
            id="w",
            start="missing",
            nodes={"step_a": Node(type="http")},
        )


def test_workflow_rejects_transition_to_unknown_node():
    with pytest.raises(ValidationError, match="unknown node 'nowhere'"):
        Workflow(
            id="w",
            start="step_a",
            nodes={"step_a": Node(type="http", transitions={"success": "nowhere"})},
        )


def test_workflow_allows_terminal_transition():
    workflow = Workflow(
        id="w",
        start="step_a",
        nodes={"step_a": Node(type="http", transitions={"success": None})},
    )
    assert workflow.nodes["step_a"].transitions["success"] is None


def test_workflow_is_immutable(single_node_workflow):
    with pytest.raises(ValidationError):
        single_node_workflow.id = "mutated"


def test_node_defaults_to_empty_params_and_transitions():
    node = Node(type="transform")
    assert node.params == {}
    assert node.transitions == {}


def test_node_is_immutable():
    node = Node(type="http")
    with pytest.raises(ValidationError):
        node.type = "form"


def test_workflow_node_params_are_preserved():
    workflow = Workflow(
        id="w",
        start="step_a",
        nodes={
            "step_a": Node(
                type="http",
                params={"url": "https://example.com", "method": "POST"},
                transitions={"success": None},
            )
        },
    )
    assert workflow.nodes["step_a"].params["url"] == "https://example.com"
