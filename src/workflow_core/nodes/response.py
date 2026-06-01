from __future__ import annotations

from typing import Any

from workflow_core.context import Context
from workflow_core.result import Result


class ResponseNode:
    async def run(self, context: Context, params: dict[str, Any]) -> Result:
        include: list[str] | None = params.get("include")
        status: int = params.get("status", 200)

        data = (
            {k: v for k, v in context.data.items() if k in include}
            if include
            else dict(context.data)
        )

        return Result(output={"response": {"data": data, "status": status}})
