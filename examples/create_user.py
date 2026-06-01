"""
Create User — declarative workflow example.

Flow:
    collect          ──success──▶  check_duplicate
                     ──failure──▶  respond_invalid

    check_duplicate  ──exists──▶   respond_conflict
                     ──free──▶     save

    save             ──success──▶  respond_created
                     ──failure──▶  respond_error

    respond_*        ──success──▶  None

Custom nodes (check_duplicate, save) demonstrate how domain-specific
logic that needs dynamic context values is encapsulated in a node,
keeping the workflow declaration clean.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from workflow_core import Node, Registry, Runtime, Workflow
from workflow_core.context import Context
from workflow_core.nodes import FormNode, ResponseNode
from workflow_core.result import NodeError, Result


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class UserRepository:
    """In-memory repository. Replace with RedisRepository in production."""

    def __init__(self) -> None:
        self._users: dict[str, dict[str, Any]] = {}

    async def get(self, key: str) -> dict[str, Any] | None:
        return self._users.get(key)

    async def set(self, key: str, value: dict[str, Any]) -> None:
        self._users[key] = value

    def _key(self, name: str) -> str:
        return f"user:{name.lower()}"


# ---------------------------------------------------------------------------
# Custom nodes
# ---------------------------------------------------------------------------

class CheckDuplicateNode:
    """Looks up a user by name from context.data["validated"]["name"].
    Returns transition="exists" if found, "free" if not."""

    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        name = context.data.get("validated", {}).get("name")
        if not name:
            return NodeError(code="MISSING_NAME", message="validated.name is required")

        existing = await self._repo.get(self._repo._key(name))
        if existing:
            return Result(output={"existing_user": existing}, transition="exists")
        return Result(transition="free")


class SaveUserNode:
    """Saves context.data["validated"] under user:{name}."""

    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        validated = context.data.get("validated", {})
        name = validated.get("name")
        if not name:
            return NodeError(code="MISSING_NAME", message="validated.name is required")

        await self._repo.set(self._repo._key(name), validated)
        return Result(output={"created": validated})


# ---------------------------------------------------------------------------
# Workflow declaration
# ---------------------------------------------------------------------------

CREATE_USER = Workflow(
    id="create_user",
    start="collect",
    nodes={

        "collect": Node(
            type="form",
            params={
                "fields": {
                    "name": {"type": "str", "required": True, "max_length": 100},
                    "age":  {"type": "int", "required": True, "min": 0, "max": 150},
                    "role": {"type": "str", "required": True, "enum": ["admin", "user", "viewer"]},
                },
            },
            transitions={
                "success": "check_duplicate",
                "failure": "respond_invalid",
            },
        ),

        "check_duplicate": Node(
            type="check_duplicate",
            transitions={
                "exists": "respond_conflict",
                "free":   "save",
            },
        ),

        "save": Node(
            type="save_user",
            transitions={
                "success": "respond_created",
                "failure": "respond_error",
            },
        ),

        "respond_created": Node(
            type="response",
            params={"status": 201, "include": ["created"]},
            transitions={"success": None},
        ),
        "respond_invalid": Node(
            type="response",
            params={"status": 422},
            transitions={"success": None},
        ),
        "respond_conflict": Node(
            type="response",
            params={"status": 409, "include": ["existing_user"]},
            transitions={"success": None},
        ),
        "respond_error": Node(
            type="response",
            params={"status": 500},
            transitions={"success": None},
        ),
    },
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def build_registry(repo: UserRepository) -> Registry:
    registry = Registry()
    registry.register("form")(FormNode)
    registry.register("response")(ResponseNode)
    registry.register("check_duplicate")(lambda: CheckDuplicateNode(repo))
    registry.register("save_user")(lambda: SaveUserNode(repo))
    return registry


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def run(label: str, runtime: Runtime, input_data: dict) -> None:
    context = await runtime.execute(label, input_data=input_data)
    response = context.data.get("response", {})
    print(f"\n── {label}")
    print(f"   status : {response.get('status')}")
    print(f"   data   : {json.dumps(response.get('data'), indent=6)}")


async def main() -> None:
    repo = UserRepository()
    registry = build_registry(repo)
    runtime = Runtime(CREATE_USER, registry)

    # 1. Valid new user
    await run(
        "valid — Alice (admin, 30)",
        runtime,
        {"input": {"name": "Alice", "age": 30, "role": "admin"}},
    )

    # 2. Duplicate
    await run(
        "duplicate — Alice again",
        runtime,
        {"input": {"name": "Alice", "age": 30, "role": "admin"}},
    )

    # 3. Validation failure
    await run(
        "invalid — bad age and unknown role",
        runtime,
        {"input": {"name": "Bob", "age": -5, "role": "superuser"}},
    )

    # 4. Valid second user — different name, should succeed
    await run(
        "valid — Carol (viewer, 25)",
        runtime,
        {"input": {"name": "Carol", "age": 25, "role": "viewer"}},
    )

    print(f"\n── repository state")
    for key, user in repo._users.items():
        print(f"   {key}: {user}")


if __name__ == "__main__":
    asyncio.run(main())
