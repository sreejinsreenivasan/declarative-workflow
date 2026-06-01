# core/entities/ — Domain Entities

Domain entities are the source of truth for what a Workflow, its Nodes, and execution
state look like. They are Pydantic v2 `BaseModel` subclasses — validated, typed, frozen.

---

## Entity Rules

- All fields use explicit types. No `Any` unless unavoidable and documented with a comment.
- Required fields have no defaults. Optional fields use `Optional[T] = None` or `Field(default_factory=...)`.
- Validators live inside the entity using `@model_validator` or `@field_validator` — not re-implemented in services.
- All entities use `model_config = ConfigDict(frozen=True)`.
- Status fields are always typed enums from `core/constants.py`, never raw strings.

---

## WorkflowDefinition

`workflow.py` defines `WorkflowDefinition` — the top-level immutable schema object.

Key constraints enforced at construction:
- `start_node` must exist in `nodes`
- Transition targets must reference nodes that exist in the definition
- Node type must be a registered `NodeType` enum value

`WorkflowDefinition` is read-only after construction. It is never mutated during execution.

---

## ExecutionContext

`context.py` defines `ExecutionContext` — the mutable execution state carrier.

Rules:
- `data` is append-only: nodes add keys, never overwrite keys set by earlier nodes
- `current_node` is the only field that transitions during execution
- `model_copy(update={...})` is the only legal way to produce an updated context
- Never pass raw `dict` across boundaries — always `ExecutionContext`

```python
# correct — produce new context
new_context = context.model_copy(update={
    "current_node": next_node,
    "data": {**context.data, "kyc_result": result},
})

# wrong — mutation
context.current_node = next_node
```

---

## NodeResult

`result.py` defines `NodeResult` and `FailedNodeResult`.

- `NodeResult` carries output data and the transition outcome key (e.g. `"success"`, `"failure"`)
- `FailedNodeResult` carries a structured `WorkflowError`
- `TransitionProcessor` reads the outcome from `NodeResult` to select the next node

No node returns a raw `dict` or raises a plain `Exception` — always a typed result.

---

## Adding New Fields

When adding a field to any entity:
- If it may contain user-supplied data, document whether it could carry PII
- If it changes the public API surface, bump the minor version in `pyproject.toml`

---

## Tests

Entity tests live in `tests/core/entities/`. They cover:
- `@model_validator` edge cases (invalid transitions, missing nodes)
- Enum serialisation (`use_enum_values=True`)
- `model_copy` round-trips preserve all invariants
- Frozen model raises `ValidationError` on direct attribute mutation
