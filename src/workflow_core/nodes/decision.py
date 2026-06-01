from __future__ import annotations

from typing import Any

from workflow_core.context import Context
from workflow_core.result import NodeError, Result

_OPERATORS = {
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
    "exists": lambda a, _: a is not None,
    "not_exists": lambda a, _: a is None,
}


class DecisionNode:
    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        key = params.get("key")
        operator = params.get("operator", "eq")
        value = params.get("value")

        if key is None:
            return NodeError(code="INVALID_PARAMS", message="'key' is required")

        if operator not in _OPERATORS:
            return NodeError(code="INVALID_OPERATOR", message=f"Unknown operator '{operator}'")

        actual = context.data.get(key)
        matched = _OPERATORS[operator](actual, value)

        return Result(transition="true" if matched else "false")
