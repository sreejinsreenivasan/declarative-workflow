from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Context(BaseModel):
    model_config = ConfigDict(frozen=True)

    execution_id: str
    workflow_id: str
    node: str | None
    data: dict[str, Any] = Field(default_factory=dict)

    def evolve(self, **changes: Any) -> Context:
        return self.model_copy(update=changes)

    def merge(self, output: dict[str, Any]) -> Context:
        return self.model_copy(update={"data": {**self.data, **output}})
