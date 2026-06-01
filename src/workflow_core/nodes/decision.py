from __future__ import annotations

from typing import Any

from workflow_core.context import Context
from workflow_core.processors import check_condition
from workflow_core.result import NodeError, Result


class DecisionNode:
    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        key = params.get("key")
        if key is None:
            return NodeError(code="INVALID_PARAMS", message="'key' is required")

        result = await check_condition(
            key=key,
            operator=params.get("operator", "eq"),
            value=params.get("value"),
        )(context)

        if isinstance(result, NodeError):
            return result

        matched = result.data.get("_matched", False)
        return Result(transition="true" if matched else "false")
