from __future__ import annotations

from typing import Any

from workflow_core.context import Context
from workflow_core.processors import validate_fields
from workflow_core.result import NodeError, Result


class FormNode:
    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        result = await validate_fields(
            params.get("fields", {}),
            source=params.get("source", "input"),
        )(context)
        if isinstance(result, NodeError):
            return result
        return Result(output={"validated": result.data.get("validated", {})})
