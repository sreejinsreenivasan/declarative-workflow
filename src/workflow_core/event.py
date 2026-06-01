from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    NODE_STARTED = "node.started"
    NODE_COMPLETED = "node.completed"
    TRANSITION_SELECTED = "transition.selected"
    CONTEXT_UPDATED = "context.updated"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"


class Event(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: EventType
    execution_id: str
    node_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)
