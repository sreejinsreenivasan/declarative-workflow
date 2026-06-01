from __future__ import annotations

from typing import Protocol

from workflow_core.context import Context


class ExecutionStore(Protocol):
    async def save(self, execution_id: str, context: Context) -> None: ...
    async def load(self, execution_id: str) -> Context | None: ...


class InMemoryStore:
    """In-memory store for development and testing."""

    def __init__(self) -> None:
        self._data: dict[str, Context] = {}

    async def save(self, execution_id: str, context: Context) -> None:
        self._data[execution_id] = context

    async def load(self, execution_id: str) -> Context | None:
        return self._data.get(execution_id)
