import pytest
from pydantic import ValidationError

from workflow_core.context import Context


@pytest.fixture
def context() -> Context:
    return Context(
        execution_id="exec_001",
        workflow_id="onboarding",
        node="collect_info",
        data={"name": "Alice"},
    )


def test_context_construction(context):
    assert context.execution_id == "exec_001"
    assert context.node == "collect_info"
    assert context.data["name"] == "Alice"


def test_context_is_immutable(context):
    with pytest.raises(ValidationError):
        context.node = "next_step"


def test_context_evolve_changes_node(context):
    updated = context.evolve(node="next_step")
    assert updated.node == "next_step"
    assert updated.execution_id == context.execution_id


def test_context_evolve_does_not_mutate_original(context):
    context.evolve(node="next_step")
    assert context.node == "collect_info"


def test_context_merge_adds_output(context):
    updated = context.merge({"age": 30})
    assert updated.data["name"] == "Alice"
    assert updated.data["age"] == 30


def test_context_merge_does_not_overwrite_existing_keys(context):
    updated = context.merge({"name": "Bob"})
    assert updated.data["name"] == "Bob"


def test_context_merge_does_not_mutate_original(context):
    context.merge({"age": 30})
    assert "age" not in context.data


def test_context_node_can_be_none():
    ctx = Context(execution_id="e1", workflow_id="w1", node=None)
    assert ctx.node is None
