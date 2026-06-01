import jinja2
import pytest

from workflow_core.context import Context
from workflow_core.nodes.ui import UINode
from workflow_core.result import NodeError, Result

TEMPLATES = {
    "form.html": (
        "<form>"
        "{% for name, field in fields.items() %}"
        "<input name='{{ name }}' value='{{ data.get(name, '') }}'/>"
        "{% if errors.get(name) %}<span>{{ errors[name] }}</span>{% endif %}"
        "{% endfor %}"
        "<span id='exec'>{{ execution_id }}</span>"
        "<span id='node'>{{ node }}</span>"
        "</form>"
    ),
    "_form.html": "<form id='partial'>{{ fields | list }}</form>",
}

FIELDS = {
    "name": {"type": "str", "required": True},
    "age":  {"type": "int", "required": True, "min": 0},
}


def make_env() -> jinja2.Environment:
    return jinja2.Environment(loader=jinja2.DictLoader(TEMPLATES))


def ctx(data: dict) -> Context:
    return Context(execution_id="exec_001", workflow_id="w1", node="step1", data=data)


def node() -> UINode:
    return UINode(make_env())


# --- GET rendering ---

async def test_get_renders_template():
    result = await node().run(
        ctx({"request": {"method": "GET"}}),
        {"template": "form.html", "fields": FIELDS},
    )
    assert isinstance(result, Result)
    assert result.transition == "render"
    assert "<form>" in result.output["html"]


async def test_get_injects_execution_id_and_node():
    result = await node().run(
        ctx({"request": {"method": "GET"}}),
        {"template": "form.html", "fields": FIELDS},
    )
    assert "exec_001" in result.output["html"]
    assert "step1" in result.output["html"]


async def test_get_injects_context_data():
    result = await node().run(
        ctx({"request": {"method": "GET"}, "name": "Alice"}),
        {"template": "form.html", "fields": FIELDS},
    )
    assert "Alice" in result.output["html"]


async def test_get_no_errors_in_template():
    result = await node().run(
        ctx({"request": {"method": "GET"}}),
        {"template": "form.html", "fields": FIELDS},
    )
    assert "<span>" not in result.output["html"]


async def test_get_uses_partial_template_when_htmx():
    result = await node().run(
        ctx({"request": {"method": "GET", "is_htmx": True}}),
        {"template": "form.html", "partial_template": "_form.html", "fields": FIELDS},
    )
    assert "partial" in result.output["html"]


async def test_get_uses_full_template_when_not_htmx():
    result = await node().run(
        ctx({"request": {"method": "GET", "is_htmx": False}}),
        {"template": "form.html", "partial_template": "_form.html", "fields": FIELDS},
    )
    assert "<form>" in result.output["html"]
    assert "partial" not in result.output["html"]


async def test_get_uses_full_template_when_no_partial_defined():
    result = await node().run(
        ctx({"request": {"method": "GET", "is_htmx": True}}),
        {"template": "form.html", "fields": FIELDS},
    )
    assert "<form>" in result.output["html"]


async def test_missing_template_param_returns_error():
    result = await node().run(
        ctx({"request": {"method": "GET"}}),
        {"fields": FIELDS},
    )
    assert isinstance(result, NodeError)
    assert result.code == "INVALID_PARAMS"


async def test_template_not_found_returns_error():
    result = await node().run(
        ctx({"request": {"method": "GET"}}),
        {"template": "missing.html", "fields": FIELDS},
    )
    assert isinstance(result, NodeError)
    assert result.code == "TEMPLATE_NOT_FOUND"


async def test_no_request_in_context_defaults_to_get():
    result = await node().run(
        ctx({}),
        {"template": "form.html", "fields": FIELDS},
    )
    assert isinstance(result, Result)
    assert result.transition == "render"


# --- POST submission ---

async def test_post_valid_input_returns_submitted():
    result = await node().run(
        ctx({"request": {"method": "POST"}, "input": {"name": "Alice", "age": 30}}),
        {"template": "form.html", "fields": FIELDS},
    )
    assert isinstance(result, Result)
    assert result.transition == "submitted"
    assert result.output["validated"] == {"name": "Alice", "age": 30}


async def test_post_invalid_input_re_renders_with_errors():
    result = await node().run(
        ctx({"request": {"method": "POST"}, "input": {"name": "Alice", "age": -1}}),
        {"template": "form.html", "fields": FIELDS},
    )
    assert isinstance(result, Result)
    assert result.transition == "error"
    assert "<span>" in result.output["html"]


async def test_post_missing_required_field_shows_error():
    result = await node().run(
        ctx({"request": {"method": "POST"}, "input": {}}),
        {"template": "form.html", "fields": FIELDS},
    )
    assert result.transition == "error"
    assert "required" in result.output["html"]


async def test_post_uses_custom_source_key():
    result = await node().run(
        ctx({"request": {"method": "POST"}, "body": {"name": "Bob", "age": 25}}),
        {"template": "form.html", "fields": FIELDS, "source": "body"},
    )
    assert result.transition == "submitted"
    assert result.output["validated"]["name"] == "Bob"


async def test_post_error_re_renders_with_htmx_partial():
    result = await node().run(
        ctx({"request": {"method": "POST", "is_htmx": True}, "input": {}}),
        {"template": "form.html", "partial_template": "_form.html", "fields": FIELDS},
    )
    assert result.transition == "error"
    assert "partial" in result.output["html"]


async def test_post_no_fields_defined_submits_empty():
    result = await node().run(
        ctx({"request": {"method": "POST"}, "input": {}}),
        {"template": "form.html", "fields": {}},
    )
    assert result.transition == "submitted"
    assert result.output["validated"] == {}
