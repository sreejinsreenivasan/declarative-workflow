from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Node(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: str
    params: dict[str, Any] = Field(default_factory=dict)
    transitions: dict[str, str | None] = Field(default_factory=dict)


class Workflow(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    start: str
    nodes: dict[str, Node]

    @model_validator(mode="after")
    def _start_exists(self) -> Workflow:
        if self.start not in self.nodes:
            raise ValueError(f"start node '{self.start}' not in nodes")
        return self

    @model_validator(mode="after")
    def _transitions_valid(self) -> Workflow:
        for node_id, node in self.nodes.items():
            for outcome, target in node.transitions.items():
                if target is not None and target not in self.nodes:
                    raise ValueError(
                        f"node '{node_id}': transition '{outcome}' → unknown node '{target}'"
                    )
        return self
