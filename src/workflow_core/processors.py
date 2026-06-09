from __future__ import annotations

from enum import Enum
from typing import Any, Awaitable, Callable, Protocol

import httpx
import jinja2

from workflow_core.context import Context
from workflow_core.result import NodeError

# ---------------------------------------------------------------------------
# Core type
# ---------------------------------------------------------------------------

Processor = Callable[[Context], Awaitable[Context | NodeError]]

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class Operator(str, Enum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"

# ---------------------------------------------------------------------------
# Repository protocol
# ---------------------------------------------------------------------------

class Repository(Protocol):
    async def get(self, key: str) -> dict[str, Any] | None: ...  # values are caller-defined
    async def set(self, key: str, value: dict[str, Any]) -> None: ...  # values are caller-defined
    async def delete(self, key: str) -> None: ...

# ---------------------------------------------------------------------------
# Combinator
# ---------------------------------------------------------------------------

def pipe(*processors: Processor) -> Processor:
    """Compose processors left to right. Short-circuits on NodeError."""
    async def _run(context: Context) -> Context | NodeError:
        for processor in processors:
            result = await processor(context)
            if isinstance(result, NodeError):
                return result
            context = result
        return context
    return _run

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_fields(fields: dict[str, Any], source: str = "input") -> Processor:  # rule specs are heterogeneous
    """Validate input fields from context.data[source]. Merges 'validated' on success."""
    async def _validate(context: Context) -> Context | NodeError:
        data = context.data.get(source) or {}
        coerced = {
            name: _coerce_field(data.get(name), fields[name])
            for name in fields
            if name in data
        }
        errors = {
            name: msg
            for name, rules in fields.items()
            if (msg := _check_field(coerced.get(name), rules)) is not None
        }
        if errors:
            return NodeError(code="VALIDATION_ERROR", message="Validation failed", details=errors)
        validated = coerced
        return context.merge({"validated": validated})
    return _validate


def _coerce_field(value: Any, rules: dict[str, Any]) -> Any:  # value/return: unknown type from form data or pre-typed input; rules: heterogeneous spec
    """Coerce string values to expected type (e.g., form data '30' → 30)."""
    if value is None or not isinstance(value, str):
        return value
    field_type = rules.get("type")
    if field_type == "int":
        try:
            return int(value)
        except ValueError:
            return value
    if field_type == "float":
        try:
            return float(value)
        except ValueError:
            return value
    if field_type == "bool":
        return value.lower() in ("true", "1", "yes", "on")
    return value


def _check_field(value: Any, rules: dict[str, Any]) -> str | None:  # value: unknown type; rules: heterogeneous spec
    if value is None:
        return "required" if rules.get("required", True) else None
    field_type = rules.get("type")
    if field_type and not _check_type(value, field_type):
        return f"must be {field_type}"
    if field_type in ("int", "float"):
        if "min" in rules and value < rules["min"]:
            return f"must be >= {rules['min']}"
        if "max" in rules and value > rules["max"]:
            return f"must be <= {rules['max']}"
    if field_type == "str":
        if "min_length" in rules and len(value) < rules["min_length"]:
            return f"must be at least {rules['min_length']} characters"
        if "max_length" in rules and len(value) > rules["max_length"]:
            return f"must be at most {rules['max_length']} characters"
    if "enum" in rules and value not in rules["enum"]:
        return f"must be one of {rules['enum']}"
    return None


def _check_type(value: Any, expected: str) -> bool:  # value: type being checked at runtime
    return {
        "str":   lambda v: isinstance(v, str),
        "int":   lambda v: isinstance(v, int) and not isinstance(v, bool),
        "float": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "bool":  lambda v: isinstance(v, bool),
    }.get(expected, lambda _: True)(value)

# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------

_OPERATORS: dict[Operator, Callable[[Any, Any], bool]] = {  # Any: comparison values are caller-defined
    Operator.EQ:         lambda a, b: a == b,
    Operator.NEQ:        lambda a, b: a != b,
    Operator.GT:         lambda a, b: a > b,
    Operator.GTE:        lambda a, b: a >= b,
    Operator.LT:         lambda a, b: a < b,
    Operator.LTE:        lambda a, b: a <= b,
    Operator.IN:         lambda a, b: a in b,
    Operator.NOT_IN:     lambda a, b: a not in b,
    Operator.EXISTS:     lambda a, _: a is not None,
    Operator.NOT_EXISTS: lambda a, _: a is None,
}


def check_condition(key: str, operator: Operator = Operator.EQ, value: Any = None) -> Processor:  # value: compared against caller-defined context data
    """Evaluate a condition against context.data[key]. Merges '_matched' bool."""
    async def _check(context: Context) -> Context | NodeError:
        if operator not in _OPERATORS:
            return NodeError(code="INVALID_OPERATOR", message=f"Unknown operator '{operator}'")
        actual = context.data.get(key)
        matched = _OPERATORS[operator](actual, value)
        return context.merge({"_matched": matched})
    return _check

# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def call_http(
    method: HttpMethod,
    url: str,
    body_key: str | None = None,
    response_key: str = "http_response",
    headers: dict[str, str] | None = None,
) -> Processor:
    """Make an async HTTP request. Merges response JSON into context."""
    async def _call(context: Context) -> Context | NodeError:
        body = context.data.get(body_key) if body_key else None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=body,
                    headers=headers or {},
                )
        except httpx.ConnectError as exc:
            return NodeError(code="CONNECTION_ERROR", message=str(exc), details={"url": url})
        if response.is_error:
            return NodeError(
                code="HTTP_ERROR",
                message=f"HTTP {response.status_code}",
                details={"status_code": response.status_code, "url": url},
            )
        return context.merge({response_key: response.json()})
    return _call

# ---------------------------------------------------------------------------
# Field mapping
# ---------------------------------------------------------------------------

def map_fields(mapping: dict[str, str]) -> Processor:
    """Map context fields using dot-path notation. Merges resolved values."""
    async def _map(context: Context) -> Context | NodeError:
        if not mapping:
            return NodeError(code="INVALID_PARAMS", message="'mapping' is required")
        output = {
            target: value
            for target, path in mapping.items()
            if (value := _resolve_path(context.data, path)) is not None
        }
        return context.merge(output)
    return _map


def _resolve_path(data: dict[str, Any], path: str) -> Any:  # data/return: context data is a heterogeneous map
    value: Any = data  # traversal cursor; type narrows as we descend into nested dicts
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value

# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def write_record(repo: Repository, key: str, data_key: str = "validated") -> Processor:
    """Write context.data[data_key] to storage at key."""
    async def _write(context: Context) -> Context | NodeError:
        await repo.set(key, context.data.get(data_key, {}))
        return context.merge({"persisted": True})
    return _write


def read_record(repo: Repository, key: str, output_key: str = "record") -> Processor:
    """Read from storage at key. NodeError(NOT_FOUND) if absent."""
    async def _read(context: Context) -> Context | NodeError:
        record = await repo.get(key)
        if record is None:
            return NodeError(code="NOT_FOUND", message=f"Record '{key}' not found")
        return context.merge({output_key: record})
    return _read


def delete_record(repo: Repository, key: str) -> Processor:
    """Delete record from storage at key."""
    async def _delete(context: Context) -> Context | NodeError:
        await repo.delete(key)
        return context.merge({"deleted": True})
    return _delete

# ---------------------------------------------------------------------------
# Response shaping
# ---------------------------------------------------------------------------

def shape_response(include: list[str] | None = None, status: int = 200) -> Processor:
    """Shape the final response. Merges 'response' dict into context."""
    async def _shape(context: Context) -> Context | NodeError:
        data = context.data
        if include:
            data = {k: v for k, v in data.items() if k in include}
        return context.merge({"response": {"data": dict(data), "status": status}})
    return _shape

# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------

def render_template(
    env: jinja2.Environment,
    template: str,
    partial: str | None = None,
    fields: dict[str, Any] | None = None,  # template context: caller-defined key/value pairs
    errors: dict[str, str] | None = None,
) -> Processor:
    """Render a Jinja2 template. Uses partial when is_htmx. Merges 'html'."""
    async def _render(context: Context) -> Context | NodeError:
        is_htmx = context.data.get("request", {}).get("is_htmx", False)
        path = partial if (is_htmx and partial) else template
        if not path:
            return NodeError(code="INVALID_PARAMS", message="'template' is required")
        try:
            tmpl = env.get_template(path)
        except jinja2.TemplateNotFound:
            return NodeError(code="TEMPLATE_NOT_FOUND", message=f"Template '{path}' not found")
        html = tmpl.render(
            data=context.data,
            fields=fields or {},
            errors=errors or {},
            execution_id=context.execution_id,
            node=context.node,
        )
        return context.merge({"html": html})
    return _render
