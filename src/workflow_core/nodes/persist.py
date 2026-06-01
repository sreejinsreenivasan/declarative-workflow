from __future__ import annotations

from typing import Any, Protocol

from workflow_core.context import Context
from workflow_core.processors import delete_record, read_record, write_record
from workflow_core.result import NodeError, Result


class Repository(Protocol):
    async def get(self, key: str) -> dict[str, Any] | None: ...
    async def set(self, key: str, value: dict[str, Any]) -> None: ...
    async def delete(self, key: str) -> None: ...


class PersistNode:
    def __init__(self, repository: Repository) -> None:
        self._repo = repository

    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        operation = params.get("operation", "write")
        key = params.get("key")

        if not key:
            return NodeError(code="INVALID_PARAMS", message="'key' is required")

        if operation == "write":
            result = await write_record(self._repo, key, params.get("data_key", "validated"))(context)
            if isinstance(result, NodeError):
                return result
            return Result(output={"persisted": True})

        if operation == "read":
            output_key = params.get("output_key", "record")
            result = await read_record(self._repo, key, output_key)(context)
            if isinstance(result, NodeError):
                return result
            return Result(output={output_key: result.data[output_key]})

        if operation == "delete":
            result = await delete_record(self._repo, key)(context)
            if isinstance(result, NodeError):
                return result
            return Result(output={"deleted": True})

        return NodeError(code="INVALID_OPERATION", message=f"Unknown operation '{operation}'")
