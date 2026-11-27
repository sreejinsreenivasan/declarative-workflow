from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from workflow_core.result import NodeError


class ExecutionStatus(str, Enum):
    RUNNING = "running"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"


class Context(BaseModel):
    model_config = ConfigDict(frozen=True)

    execution_id: str
    workflow_id: str
    node: str | None
    data: dict[str, Any] = Field(default_factory=dict)  # Any: node outputs are user-defined
    status: ExecutionStatus = ExecutionStatus.RUNNING
    error: NodeError | None = None  # set when status is FAILED

    def evolve(self, **changes: Any) -> Context:  # Any: mirrors model_copy's update values
        return self.model_copy(update=changes)

    def merge(self, output: dict[str, Any]) -> Context:  # Any: node outputs are user-defined
        return self.model_copy(update={"data": {**self.data, **output}})
