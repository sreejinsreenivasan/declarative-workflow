# Example: User Registration

Accepts a name, age, and role. Validates input, checks for conflicts, persists the user, and returns a response.

---

## Flow

```
collect_info  ──success──▶  check_exists
              ──failure──▶  respond_invalid

check_exists  ──true───▶  respond_conflict   (user already exists)
              ──false──▶  save_user

save_user     ──success──▶  respond_created
              ──failure──▶  respond_error

respond_*     ──success──▶  None
```

---

## Code

```python
import asyncio
from workflow_core import Workflow, Node, Runtime, Registry
from workflow_core.nodes import FormNode, DecisionNode, PersistNode, ResponseNode


def build_registry(repo) -> Registry:
    registry = Registry()
    registry.register("form")(FormNode)
    registry.register("decision")(DecisionNode)
    registry.register("persist")(lambda: PersistNode(repo))
    registry.register("response")(ResponseNode)
    return registry


workflow = Workflow(
    id="user_registration",
    start="collect_info",
    nodes={
        "collect_info": Node(
            type="form",
            params={
                "fields": {
                    "name": {"type": "str",  "required": True,  "max_length": 100},
                    "age":  {"type": "int",  "required": True,  "min": 0, "max": 150},
                    "role": {"type": "str",  "required": True,  "enum": ["admin", "user"]},
                }
            },
            transitions={
                "success": "check_exists",
                "failure": "respond_invalid",
            },
        ),

        "check_exists": Node(
            type="decision",
            params={"key": "existing_user", "operator": "exists"},
            transitions={
                "true":  "respond_conflict",
                "false": "save_user",
            },
        ),

        "save_user": Node(
            type="persist",
            params={
                "operation": "write",
                "key": "user:new",
                "data_key": "validated",
            },
            transitions={
                "success": "respond_created",
                "failure": "respond_error",
            },
        ),

        "respond_created": Node(
            type="response",
            params={"status": 201, "include": ["validated"]},
            transitions={"success": None},
        ),
        "respond_invalid": Node(
            type="response",
            params={"status": 422},
            transitions={"success": None},
        ),
        "respond_conflict": Node(
            type="response",
            params={"status": 409},
            transitions={"success": None},
        ),
        "respond_error": Node(
            type="response",
            params={"status": 500},
            transitions={"success": None},
        ),
    },
)


async def main():
    from unittest.mock import AsyncMock

    # mock repository for the example
    repo = AsyncMock()
    repo.get.return_value = None   # user does not exist
    repo.set = AsyncMock()

    registry = build_registry(repo)
    runtime = Runtime(workflow, registry)

    context = await runtime.execute(
        execution_id="exec_001",
        input_data={
            "input": {"name": "Alice", "age": 30, "role": "admin"},
        },
    )

    print(context.data["response"])
    # {"data": {"validated": {"name": "Alice", "age": 30, "role": "admin"}}, "status": 201}


asyncio.run(main())
```

---

## What happens step by step

| Step | Node | Input | Output |
|------|------|-------|--------|
| 1 | `collect_info` | `context.data["input"]` | `context.data["validated"]` |
| 2 | `check_exists` | `context.data["existing_user"]` | `transition="false"` (not found) |
| 3 | `save_user` | `context.data["validated"]` | `context.data["persisted"] = True` |
| 4 | `respond_created` | `context.data["validated"]` | `context.data["response"]` |

---

## Failure scenarios

**Validation fails** (e.g. age is -1):
- `collect_info` → `NodeError` → `transition="failure"` → `respond_invalid` → 422

**User already exists** (e.g. `existing_user` is in context):
- `check_exists` → `transition="true"` → `respond_conflict` → 409

**Persist fails** (repository error):
- `save_user` → `NodeError` → `transition="failure"` → `respond_error` → 500
