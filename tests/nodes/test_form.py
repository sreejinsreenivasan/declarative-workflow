import pytest

from workflow_core.context import Context
from workflow_core.nodes.form import FormNode
from workflow_core.result import NodeError, Result


def ctx(data: dict) -> Context:
    return Context(execution_id="e1", workflow_id="w1", node="form", data=data)


FIELDS = {
    "name": {"type": "str", "required": True},
    "age": {"type": "int", "required": True, "min": 0, "max": 150},
    "role": {"type": "str", "required": True, "enum": ["admin", "user"]},
}


async def test_valid_input_returns_result():
    result = await FormNode().run(
        ctx({"input": {"name": "Alice", "age": 30, "role": "admin"}}),
        {"fields": FIELDS},
    )
    assert isinstance(result, Result)
    assert result.output["validated"] == {"name": "Alice", "age": 30, "role": "admin"}


async def test_missing_required_field_returns_error():
    result = await FormNode().run(
        ctx({"input": {"name": "Alice", "age": 30}}),
        {"fields": FIELDS},
    )
    assert isinstance(result, NodeError)
    assert result.code == "VALIDATION_ERROR"
    assert "role" in result.details


async def test_wrong_type_returns_error():
    result = await FormNode().run(
        ctx({"input": {"name": "Alice", "age": "thirty", "role": "admin"}}),
        {"fields": FIELDS},
    )
    assert isinstance(result, NodeError)
    assert "age" in result.details


async def test_value_below_min_returns_error():
    result = await FormNode().run(
        ctx({"input": {"name": "Alice", "age": -1, "role": "admin"}}),
        {"fields": FIELDS},
    )
    assert isinstance(result, NodeError)
    assert "age" in result.details


async def test_value_above_max_returns_error():
    result = await FormNode().run(
        ctx({"input": {"name": "Alice", "age": 200, "role": "admin"}}),
        {"fields": FIELDS},
    )
    assert isinstance(result, NodeError)
    assert "age" in result.details


async def test_invalid_enum_returns_error():
    result = await FormNode().run(
        ctx({"input": {"name": "Alice", "age": 30, "role": "superuser"}}),
        {"fields": FIELDS},
    )
    assert isinstance(result, NodeError)
    assert "role" in result.details


async def test_multiple_errors_returned_together():
    result = await FormNode().run(
        ctx({"input": {}}),
        {"fields": FIELDS},
    )
    assert isinstance(result, NodeError)
    assert len(result.details) == 3


async def test_optional_field_absent_is_valid():
    fields = {"nickname": {"type": "str", "required": False}}
    result = await FormNode().run(ctx({"input": {}}), {"fields": fields})
    assert isinstance(result, Result)


async def test_custom_source_key():
    result = await FormNode().run(
        ctx({"body": {"name": "Alice", "age": 30, "role": "admin"}}),
        {"fields": FIELDS, "source": "body"},
    )
    assert isinstance(result, Result)


async def test_string_min_max_length():
    fields = {"code": {"type": "str", "min_length": 3, "max_length": 6}}
    short = await FormNode().run(ctx({"input": {"code": "ab"}}), {"fields": fields})
    assert isinstance(short, NodeError)

    valid = await FormNode().run(ctx({"input": {"code": "abc"}}), {"fields": fields})
    assert isinstance(valid, Result)
