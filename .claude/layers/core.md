# src/workflow_core/ — Pure Domain Logic

`core/` is the heart of the library. It contains zero framework imports.
Nothing here knows about FastAPI, Redis, httpx, or any infrastructure.

Any file in `core/` that imports from `nodes/` or `adapters/` is a critical violation — reject immediately.

Detailed rules per sub-layer:

- Execution engine → `core/execution/AGENTS.md`
- Domain entities → `core/entities/AGENTS.md`
- Node protocol → `core/nodes/AGENTS.md`

---

## Purity Rules

A module is pure if:
- It imports only from the Python standard library, Pydantic, or other `core/` modules
- All functions with the same inputs always produce the same outputs
- No function performs I/O (`await`, file reads, network calls)

If a function needs I/O, it belongs in `adapters/`. Pass the result of I/O into a
pure `core/` function rather than moving I/O inside it.

---

## Functional Composition

Prefer composing small pure functions over complex classes.

```python
def filter_pending_nodes(nodes: dict[str, NodeState]) -> list[str]:
    return [nid for nid, state in nodes.items() if state.status == NodeStatus.PENDING]

def resolve_transition(transitions: dict[str, str | None], outcome: str) -> str | None:
    return transitions.get(outcome)
```

These are trivially testable, composable, and have no side effects.

---

## Immutability

All domain entities use `model_config = ConfigDict(frozen=True)`.
Use `model.model_copy(update={...})` to produce modified instances — never mutate attributes directly.

```python
# correct
updated = context.model_copy(update={"current_node": next_node})

# wrong — mutates shared state
context.current_node = next_node
```

---

## Enums Over Magic Strings

All status values, node types, and transition outcomes are enums defined in `core/constants.py`.

```python
# correct
if status == NodeStatus.COMPLETED:

# wrong
if status == "completed":
```

---

## Sub-Module Map

| Module | Responsibility |
|--------|---------------|
| `core/entities/` | `WorkflowDefinition`, `ExecutionContext`, `NodeResult` |
| `core/execution/` | `PipelineExecutor`, `StateManager` |
| `core/nodes/` | `NodeProtocol`, `NodeInputs`, `NodeConfig` |
| `core/constants.py` | System-wide enums: `NodeStatus`, `ExecutionStatus`, `NodeType` |
