from __future__ import annotations

from typing import Any, Protocol

from workflow_core.context import Context
from workflow_core.result import NodeError, Result


class NodeProtocol(Protocol):
    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        ...
