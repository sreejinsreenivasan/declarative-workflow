import pytest

from workflow_core.workflow import Node, Workflow


@pytest.fixture
def single_node_workflow() -> Workflow:
    return Workflow(
        id="test",
        start="step_a",
        nodes={"step_a": Node(type="http", transitions={"success": None})},
    )


@pytest.fixture
def linear_workflow() -> Workflow:
    return Workflow(
        id="linear",
        start="step_a",
        nodes={
            "step_a": Node(type="form", transitions={"success": "step_b"}),
            "step_b": Node(type="http", transitions={"success": "step_c"}),
            "step_c": Node(type="response", transitions={"success": None}),
        },
    )
