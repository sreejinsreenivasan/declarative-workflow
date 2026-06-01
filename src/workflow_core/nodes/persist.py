from __future__ import annotations

from typing import Any, Protocol


from workflow_core.context import Context
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
            return await self._write(context, params, key)

        if operation == "read":
            return await self._read(params, key)

        if operation == "delete":
            await self._repo.delete(key)
            return Result(output={"deleted": True})

        return NodeError(code="INVALID_OPERATION", message=f"Unknown operation '{operation}'")

    async def _write(self, context: Context, params: dict[str, Any], key: str) -> Result:
        data_key = params.get("data_key", "validated")
        value = context.data.get(data_key, {})
        await self._repo.set(key, value)
        return Result(output={"persisted": True})

    async def _read(self, params: dict[str, Any], key: str) -> Result | NodeError:
        record = await self._repo.get(key)
        if record is None:
            return NodeError(code="NOT_FOUND", message=f"Record '{key}' not found")
        output_key = params.get("output_key", "record")
        return Result(output={output_key: record})
