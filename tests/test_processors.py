"""
Unit tests for processors in isolation.
Processors are pure async functions — tested without node wrappers.
"""
from unittest.mock import AsyncMock

import jinja2
import pytest

from workflow_core.context import Context
from workflow_core.processors import (
    call_http,
    check_condition,
    delete_record,
    map_fields,
    pipe,
    read_record,
    render_template,
    shape_response,
    validate_fields,
    write_record,
)
from workflow_core.result import NodeError


def ctx(data: dict = {}) -> Context:
    return Context(execution_id="e1", workflow_id="w1", node="step", data=data)


# ---------------------------------------------------------------------------
# pipe
# ---------------------------------------------------------------------------

async def test_pipe_runs_processors_in_order():
    calls = []

    async def p1(c: Context) -> Context:
        calls.append("p1")
        return c.merge({"p1": True})

    async def p2(c: Context) -> Context:
        calls.append("p2")
        return c.merge({"p2": True})

    result = await pipe(p1, p2)(ctx())
    assert calls == ["p1", "p2"]
    assert result.data["p1"] is True
    assert result.data["p2"] is True


async def test_pipe_short_circuits_on_node_error():
    calls = []

    async def fail(c: Context) -> NodeError:
        calls.append("fail")
        return NodeError(code="ERR", message="stop")

    async def never(c: Context) -> Context:
        calls.append("never")
        return c

    result = await pipe(fail, never)(ctx())
    assert isinstance(result, NodeError)
    assert calls == ["fail"]


async def test_pipe_with_single_processor():
    async def add_x(c: Context) -> Context:
        return c.merge({"x": 1})

    result = await pipe(add_x)(ctx())
    assert result.data["x"] == 1


async def test_pipe_empty_returns_context_unchanged():
    c = ctx({"a": 1})
    result = await pipe()(c)
    assert result.data == {"a": 1}


# ---------------------------------------------------------------------------
# validate_fields
# ---------------------------------------------------------------------------

FIELDS = {
    "name": {"type": "str",  "required": True},
    "age":  {"type": "int",  "required": True, "min": 0, "max": 150},
    "role": {"type": "str",  "required": True, "enum": ["admin", "user"]},
}


async def test_validate_fields_success():
    result = await validate_fields(FIELDS)(
        ctx({"input": {"name": "Alice", "age": 30, "role": "admin"}})
    )
    assert isinstance(result, Context)
    assert result.data["validated"] == {"name": "Alice", "age": 30, "role": "admin"}


async def test_validate_fields_missing_required():
    result = await validate_fields(FIELDS)(ctx({"input": {"name": "Alice"}}))
    assert isinstance(result, NodeError)
    assert "age" in result.details
    assert "role" in result.details


async def test_validate_fields_type_error():
    result = await validate_fields(FIELDS)(
        ctx({"input": {"name": "Alice", "age": "old", "role": "admin"}})
    )
    assert isinstance(result, NodeError)
    assert "age" in result.details


async def test_validate_fields_enum_error():
    result = await validate_fields(FIELDS)(
        ctx({"input": {"name": "Alice", "age": 30, "role": "god"}})
    )
    assert isinstance(result, NodeError)
    assert "role" in result.details


async def test_validate_fields_custom_source():
    result = await validate_fields({"x": {"type": "int"}}, source="body")(
        ctx({"body": {"x": 5}})
    )
    assert isinstance(result, Context)
    assert result.data["validated"]["x"] == 5


async def test_validate_fields_optional_absent_is_ok():
    result = await validate_fields({"nick": {"required": False}})(ctx({"input": {}}))
    assert isinstance(result, Context)


# ---------------------------------------------------------------------------
# check_condition
# ---------------------------------------------------------------------------

async def test_check_condition_eq_match():
    result = await check_condition("status", "eq", "approved")(ctx({"status": "approved"}))
    assert isinstance(result, Context)
    assert result.data["_matched"] is True


async def test_check_condition_eq_no_match():
    result = await check_condition("status", "eq", "approved")(ctx({"status": "pending"}))
    assert result.data["_matched"] is False


async def test_check_condition_exists():
    result = await check_condition("user", "exists")(ctx({"user": "Alice"}))
    assert result.data["_matched"] is True


async def test_check_condition_not_exists():
    result = await check_condition("user", "not_exists")(ctx({}))
    assert result.data["_matched"] is True


async def test_check_condition_in_operator():
    result = await check_condition("role", "in", ["admin", "owner"])(ctx({"role": "admin"}))
    assert result.data["_matched"] is True


async def test_check_condition_unknown_operator():
    result = await check_condition("x", "regex", ".*")(ctx({"x": "hello"}))
    assert isinstance(result, NodeError)
    assert result.code == "INVALID_OPERATOR"


# ---------------------------------------------------------------------------
# map_fields
# ---------------------------------------------------------------------------

async def test_map_fields_flat():
    result = await map_fields({"user_name": "validated.name"})(
        ctx({"validated": {"name": "Alice"}})
    )
    assert isinstance(result, Context)
    assert result.data["user_name"] == "Alice"


async def test_map_fields_nested_path():
    result = await map_fields({"score": "kyc.result.score"})(
        ctx({"kyc": {"result": {"score": 95}}})
    )
    assert result.data["score"] == 95


async def test_map_fields_missing_path_excluded():
    result = await map_fields({"a": "exists", "b": "missing"})(ctx({"exists": 1}))
    assert "a" in result.data
    assert "b" not in result.data


async def test_map_fields_empty_mapping_returns_error():
    result = await map_fields({})(ctx({}))
    assert isinstance(result, NodeError)


# ---------------------------------------------------------------------------
# write_record / read_record / delete_record
# ---------------------------------------------------------------------------

def make_repo(record=None):
    repo = AsyncMock()
    repo.get = AsyncMock(return_value=record)
    repo.set = AsyncMock()
    repo.delete = AsyncMock()
    return repo


async def test_write_record_calls_set():
    repo = make_repo()
    result = await write_record(repo, "user:1")(ctx({"validated": {"name": "Alice"}}))
    repo.set.assert_awaited_once_with("user:1", {"name": "Alice"})
    assert isinstance(result, Context)
    assert result.data["persisted"] is True


async def test_read_record_found():
    repo = make_repo(record={"name": "Alice"})
    result = await read_record(repo, "user:1")(ctx({}))
    assert isinstance(result, Context)
    assert result.data["record"] == {"name": "Alice"}


async def test_read_record_not_found():
    repo = make_repo(record=None)
    result = await read_record(repo, "user:99")(ctx({}))
    assert isinstance(result, NodeError)
    assert result.code == "NOT_FOUND"


async def test_read_record_custom_output_key():
    repo = make_repo(record={"x": 1})
    result = await read_record(repo, "k", output_key="user")(ctx({}))
    assert "user" in result.data


async def test_delete_record_calls_delete():
    repo = make_repo()
    result = await delete_record(repo, "user:1")(ctx({}))
    repo.delete.assert_awaited_once_with("user:1")
    assert result.data["deleted"] is True


# ---------------------------------------------------------------------------
# shape_response
# ---------------------------------------------------------------------------

async def test_shape_response_includes_all_data():
    result = await shape_response()(ctx({"name": "Alice", "age": 30}))
    assert result.data["response"]["data"] == {"name": "Alice", "age": 30}
    assert result.data["response"]["status"] == 200


async def test_shape_response_custom_status():
    result = await shape_response(status=201)(ctx({"name": "Alice"}))
    assert result.data["response"]["status"] == 201


async def test_shape_response_include_filter():
    result = await shape_response(include=["name"])(ctx({"name": "Alice", "secret": "x"}))
    assert "name" in result.data["response"]["data"]
    assert "secret" not in result.data["response"]["data"]


# ---------------------------------------------------------------------------
# render_template
# ---------------------------------------------------------------------------

TEMPLATES = {
    "form.html":  "<form>{{ fields | list }}</form>",
    "_form.html": "<partial>{{ errors }}</partial>",
}


def make_env() -> jinja2.Environment:
    return jinja2.Environment(loader=jinja2.DictLoader(TEMPLATES))


async def test_render_template_success():
    result = await render_template(make_env(), "form.html", fields={"name": {}})(ctx({}))
    assert isinstance(result, Context)
    assert "<form>" in result.data["html"]


async def test_render_template_uses_partial_for_htmx():
    result = await render_template(make_env(), "form.html", partial="_form.html")(
        ctx({"request": {"is_htmx": True}})
    )
    assert "<partial>" in result.data["html"]


async def test_render_template_uses_full_when_not_htmx():
    result = await render_template(make_env(), "form.html", partial="_form.html")(ctx({}))
    assert "<form>" in result.data["html"]


async def test_render_template_not_found():
    result = await render_template(make_env(), "missing.html")(ctx({}))
    assert isinstance(result, NodeError)
    assert result.code == "TEMPLATE_NOT_FOUND"


async def test_render_template_missing_path():
    result = await render_template(make_env(), "")(ctx({}))
    assert isinstance(result, NodeError)
    assert result.code == "INVALID_PARAMS"


# ---------------------------------------------------------------------------
# pipe + processors composition
# ---------------------------------------------------------------------------

async def test_pipe_validate_then_map():
    """Compose validate_fields and map_fields — demonstrates reuse."""
    result = await pipe(
        validate_fields({"name": {"type": "str"}}),
        map_fields({"user_name": "validated.name"}),
    )(ctx({"input": {"name": "Alice"}}))

    assert isinstance(result, Context)
    assert result.data["validated"]["name"] == "Alice"
    assert result.data["user_name"] == "Alice"


async def test_pipe_stops_at_first_error():
    """If validate fails, map never runs."""
    result = await pipe(
        validate_fields({"age": {"type": "int", "required": True}}),
        map_fields({"years": "validated.age"}),
    )(ctx({"input": {}}))

    assert isinstance(result, NodeError)
    assert "age" in result.details
    assert "years" not in (result.details if isinstance(result, NodeError) else {})
