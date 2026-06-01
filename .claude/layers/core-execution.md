# core/execution/ — Execution Engine

The execution engine is the most critical module in the library.
It drives execution through a workflow definition node by node,
manages pipeline composition, and produces state transitions.

---

## Key Concepts

| Concept | Type | Description |
|---------|------|-------------|
| `PipelineExecutor` | class | Runs processor chains; supports both sync and async processors |
| `StateManager` | module | Pure functions for `ExecutionContext` transitions |
| `WorkflowRuntime` | class (in `runtime.py`) | Top-level orchestrator; drives the node loop |

---

## Execution Invariants

These must never be broken:

1. **A node executes only once per path** — check `NodeStatus` before execution; skip if `COMPLETED`
2. **Context is append-only** — processors and nodes add to `context.data`; they never delete or overwrite existing keys
3. **WorkflowDefinition is never mutated during execution** — it is read-only; all mutable state lives in `ExecutionContext`
4. **State is persisted before and after each node** — the repository is called at both checkpoints

---

## PipelineExecutor

`executor.py` runs a list of processors sequentially against an `ExecutionContext`.

Rules:
- Supports both sync (`def run`) and async (`async def run`) processors transparently
- Returns a new `ExecutionContext` after each processor — never mutates in place
- If any processor returns a `FailedNodeResult`, execution stops and the failure propagates
- `execute()` is the sync path (Django / testing); `execute_async()` is the async path (FastAPI)

```python
# sync processor — plain def
class ValidationProcessor:
    def run(self, context: ExecutionContext) -> ExecutionContext: ...

# async processor — async def
class HTTPProcessor:
    async def run(self, context: ExecutionContext) -> ExecutionContext: ...
```

The executor checks `asyncio.iscoroutinefunction(processor.run)` to dispatch correctly.

---

## StateManager

`state_manager.py` contains only pure functions that produce new `ExecutionContext` instances.

```python
def advance_to_node(context: ExecutionContext, node_id: str | None) -> ExecutionContext:
    return context.model_copy(update={"current_node": node_id})

def mark_node_completed(context: ExecutionContext, node_id: str) -> ExecutionContext:
    updated_states = {**context.node_states, node_id: NodeStatus.COMPLETED}
    return context.model_copy(update={"node_states": updated_states})
```

Never mutate `ExecutionContext` in `StateManager`. Always return a new instance.

---

## Tests

Tests live in `tests/core/execution/`. Each test:
- Builds a minimal `WorkflowDefinition` with 1–3 nodes
- Drives it through `WorkflowRuntime` or `PipelineExecutor` directly
- Asserts the resulting `ExecutionContext` state
- Uses no mocks for core execution logic — test the real path

Async tests use `async def` and are auto-discovered via `asyncio_mode = auto`.
