# Context

```python
from workflow_core import Context
```

Carries all execution state through the workflow. Immutable — every modification produces a new instance.

---

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `execution_id` | `str` | Identifies the execution run |
| `workflow_id` | `str` | ID of the workflow being executed |
| `node` | `str \| None` | Current node ID. `None` when the workflow has ended |
| `data` | `dict[str, Any]` | Accumulated execution data |

---

## Methods

### `evolve(**changes) → Context`

Produces a new `Context` with the given fields changed. All other fields are preserved.

```python
next_context = context.evolve(node="next_step")
```

Used by the runtime to advance to the next node.

### `merge(output: dict) → Context`

Produces a new `Context` with `output` merged into `data`. Existing keys in `data` are overwritten by keys in `output`.

```python
updated = context.merge({"user_id": 42, "email": "a@b.com"})
```

Used by the runtime after each node completes to incorporate node output.

---

## Immutability

`Context` is a frozen Pydantic model. Direct attribute assignment raises `ValidationError`:

```python
context.node = "next"  # raises ValidationError
```

Always use `evolve()` or `merge()`:

```python
context = context.evolve(node="next")
context = context.merge({"result": value})
```

---

## Data is append-only by convention

The runtime merges node output using `merge()`, which can overwrite earlier keys if a later node produces the same key. By convention, nodes should use distinct output keys to preserve the full execution record in `context.data`.

---

## Example

```python
# initial context (created by Runtime)
context = Context(
    execution_id="exec_001",
    workflow_id="onboarding",
    node="collect_info",
    data={"input": {"name": "Alice", "age": 30}},
)

# after FormNode runs:
context = context.merge({"validated": {"name": "Alice", "age": 30}}).evolve(node="verify_kyc")

# after HTTPNode runs:
context = context.merge({"kyc_result": {"status": "approved"}}).evolve(node="create_account")

# final context (node is None → workflow ended)
context.data
# {
#   "input":       {"name": "Alice", "age": 30},
#   "validated":   {"name": "Alice", "age": 30},
#   "kyc_result":  {"status": "approved"},
#   "response":    {"data": {...}, "status": 201},
# }
```
