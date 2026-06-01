from __future__ import annotations

from typing import Any

from workflow_core.context import Context
from workflow_core.result import NodeError, Result


class TransformNode:
    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        mapping = params.get("mapping", {})

        if not mapping:
            return NodeError(code="INVALID_PARAMS", message="'mapping' is required")

        output = {
            target: value
            for target, path in mapping.items()
            if (value := _resolve(context.data, path)) is not None
        }

        return Result(output=output)


def _resolve(data: dict[str, Any], path: str) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value
