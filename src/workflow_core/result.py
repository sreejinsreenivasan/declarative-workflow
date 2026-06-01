from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Result(BaseModel):
    model_config = ConfigDict(frozen=True)

    output: dict[str, Any] = Field(default_factory=dict)
    transition: str = "success"


class NodeError(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    transition: str = "failure"
