import pytest

from workflow_core.context import Context
from workflow_core.nodes.transform import TransformNode
from workflow_core.result import NodeError, Result


def ctx(data: dict) -> Context:
    return Context(execution_id="e1", workflow_id="w1", node="transform", data=data)


async def test_flat_mapping():
    result = await TransformNode().run(
        ctx({"validated": {"name": "Alice", "age": 30}}),
        {"mapping": {"user_name": "validated.name", "user_age": "validated.age"}},
    )
    assert isinstance(result, Result)
    assert result.output == {"user_name": "Alice", "user_age": 30}


async def test_nested_path_resolution():
    result = await TransformNode().run(
        ctx({"a": {"b": {"c": "deep"}}}),
        {"mapping": {"value": "a.b.c"}},
    )
    assert result.output["value"] == "deep"


async def test_missing_path_excluded_from_output():
    result = await TransformNode().run(
        ctx({"validated": {"name": "Alice"}}),
        {"mapping": {"user_name": "validated.name", "user_age": "validated.age"}},
    )
    assert "user_name" in result.output
    assert "user_age" not in result.output


async def test_empty_mapping_returns_error():
    result = await TransformNode().run(ctx({}), {"mapping": {}})
    assert isinstance(result, NodeError)
    assert result.code == "INVALID_PARAMS"


async def test_no_mapping_key_returns_error():
    result = await TransformNode().run(ctx({}), {})
    assert isinstance(result, NodeError)


async def test_top_level_key_mapping():
    result = await TransformNode().run(
        ctx({"name": "Bob"}),
        {"mapping": {"username": "name"}},
    )
    assert result.output["username"] == "Bob"
