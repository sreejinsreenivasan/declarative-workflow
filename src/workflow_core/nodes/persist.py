from __future__ import annotations

from enum import Enum
from typing import Any

from workflow_core.context import Context
from workflow_core.processors import Repository, delete_record, read_record, write_record
from workflow_core.result import NodeError, Result


class OperationType(str, Enum):
    WRITE = "write"
    READ = "read"
    DELETE = "delete"


class PersistNode:
    def __init__(self, repository: Repository) -> None:
        self._repo = repository

    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:  # params: caller-defined node config
        raw_op = params.get("operation", OperationType.WRITE)
        try:
            operation = OperationType(raw_op)
        except ValueError:
            return NodeError(code="INVALID_OPERATION", message=f"Unknown operation '{raw_op}'")

        key = params.get("key")
        if not key:
            return NodeError(code="INVALID_PARAMS", message="'key' is required")

        if operation == OperationType.WRITE:
            result = await write_record(self._repo, key, params.get("data_key", "validated"))(context)
            if isinstance(result, NodeError):
                return result
            return Result(output={"persisted": True})

        if operation == OperationType.READ:
            output_key = params.get("output_key", "record")
            result = await read_record(self._repo, key, output_key)(context)
            if isinstance(result, NodeError):
                return result
            return Result(output={output_key: result.data[output_key]})

        if operation == OperationType.DELETE:
            result = await delete_record(self._repo, key)(context)
            if isinstance(result, NodeError):
                return result
            return Result(output={"deleted": True})

        return NodeError(code="INVALID_OPERATION", message=f"Unknown operation '{operation}'")
