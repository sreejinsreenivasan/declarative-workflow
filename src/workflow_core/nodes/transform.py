from __future__ import annotations

from typing import Any

from workflow_core.context import Context
from workflow_core.processors import map_fields
from workflow_core.result import NodeError, Result


class TransformNode:
    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        mapping = params.get("mapping", {})

        result = await map_fields(mapping)(context)

        if isinstance(result, NodeError):
            return result

        output = {target: result.data[target] for target in mapping if target in result.data}
        return Result(output=output)
