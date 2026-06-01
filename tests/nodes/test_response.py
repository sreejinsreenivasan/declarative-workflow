import pytest

from workflow_core.context import Context
from workflow_core.nodes.response import ResponseNode
from workflow_core.result import Result


def ctx(data: dict) -> Context:
    return Context(execution_id="e1", workflow_id="w1", node="response", data=data)


async def test_returns_all_context_data_by_default():
    result = await ResponseNode().run(
        ctx({"name": "Alice", "age": 30}),
        {},
    )
    assert isinstance(result, Result)
    assert result.output["response"]["data"] == {"name": "Alice", "age": 30}


async def test_default_status_is_200():
    result = await ResponseNode().run(ctx({"x": 1}), {})
    assert result.output["response"]["status"] == 200


async def test_custom_status_code():
    result = await ResponseNode().run(ctx({"x": 1}), {"status": 201})
    assert result.output["response"]["status"] == 201


async def test_include_filters_keys():
    result = await ResponseNode().run(
        ctx({"name": "Alice", "age": 30, "internal_id": "xyz"}),
        {"include": ["name", "age"]},
    )
    data = result.output["response"]["data"]
    assert "name" in data
    assert "age" in data
    assert "internal_id" not in data


async def test_include_with_missing_key_omits_it():
    result = await ResponseNode().run(
        ctx({"name": "Alice"}),
        {"include": ["name", "missing_key"]},
    )
    data = result.output["response"]["data"]
    assert "name" in data
    assert "missing_key" not in data


async def test_empty_context_returns_empty_data():
    result = await ResponseNode().run(ctx({}), {})
    assert result.output["response"]["data"] == {}
