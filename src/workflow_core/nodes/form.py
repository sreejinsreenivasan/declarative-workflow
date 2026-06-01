from __future__ import annotations

from typing import Any

from workflow_core.context import Context
from workflow_core.result import NodeError, Result


class FormNode:
    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        source = params.get("source", "input")
        fields = params.get("fields", {})
        data = context.data.get(source) or {}

        errors = {
            name: msg
            for name, rules in fields.items()
            if (msg := _validate_field(name, data.get(name), rules)) is not None
        }

        if errors:
            return NodeError(code="VALIDATION_ERROR", message="Validation failed", details=errors)

        validated = {name: data[name] for name in fields if name in data}
        return Result(output={"validated": validated})


def _validate_field(name: str, value: Any, rules: dict[str, Any]) -> str | None:
    required = rules.get("required", True)

    if value is None:
        return "required" if required else None

    field_type = rules.get("type")
    if field_type and not _check_type(value, field_type):
        return f"must be {field_type}"

    if field_type == "int" or field_type == "float":
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


def _check_type(value: Any, expected: str) -> bool:
    return {
        "str": lambda v: isinstance(v, str),
        "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "float": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "bool": lambda v: isinstance(v, bool),
    }.get(expected, lambda _: True)(value)
