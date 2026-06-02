from __future__ import annotations

from typing import Any

from workflow_core.context import Context
from workflow_core.processors import shape_response
from workflow_core.result import NodeError, Result


class ResponseNode:
    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        result = await shape_response(
            include=params.get("include"),
            status=params.get("status", 200),
        )(context)

        if isinstance(result, NodeError):
            return result

        return Result(output={"response": result.data["response"]}, transition="success")
