# Architecture Rules

These rules apply to all files in `src/workflow_core/`.

---

## Layer Boundary — Non-Negotiable

```
adapters/  →  nodes/  →  entities/ + execution/
```

- `entities/` and `execution/` import only stdlib and Pydantic
- `nodes/` imports from `entities/` and `execution/` only — never from `adapters/`
- `adapters/` imports from `nodes/`, `entities/`, and `execution/`

Any import that violates this direction is a BLOCKER in review.

---

## What Belongs Where

| Logic | Location |
|-------|----------|
| Domain entities (`WorkflowDefinition`, `ExecutionContext`) | `src/workflow_core/entities/` |
| Execution orchestration (`PipelineExecutor`, `StateManager`) | `src/workflow_core/execution/` |
| Node contract (`NodeProtocol`, `NodeInputs`, `NodeResult`) | `src/workflow_core/nodes/protocol.py` |
| Built-in node implementations | `src/workflow_core/nodes/` |
| Framework integration (FastAPI router, Redis client) | `src/workflow_core/adapters/` |
| Business rules, field validation logic | `entities/` or `execution/` only |
| HTTP request/response shaping | `adapters/` only |

---

## Approval Gate

Present a plan and wait for explicit approval before modifying:
- `src/workflow_core/execution/executor.py`
- `src/workflow_core/execution/state_manager.py`
- `src/workflow_core/entities/` (any file)
- `src/workflow_core/nodes/protocol.py`
- `src/workflow_core/runtime.py`

These files define execution semantics and public API contracts.
Changes here can silently break user-defined nodes or persisted execution state.

---

## DI Pattern

Framework objects (Redis client, httpx client) are never instantiated inside nodes or core.
They are injected via the adapter layer.

```python
# correct — injected at adapter boundary
class RedisRepository(AbstractRepository):
    def __init__(self, client: redis.asyncio.Redis): ...

# wrong — node instantiates its own infrastructure
class HTTPNode:
    def __init__(self):
        self.client = httpx.AsyncClient()  # violates layer boundary
```
