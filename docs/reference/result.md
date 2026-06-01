# Result & NodeError

```python
from workflow_core import Result, NodeError
```

Every node returns either a `Result` (success path) or a `NodeError` (failure path). Both are immutable Pydantic models.

---

## Result

A successful node outcome.

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `output` | `dict[str, Any]` | `{}` | Data merged into `context.data` by the runtime |
| `transition` | `str` | `"success"` | Key used to select the next state |

### Examples

```python
# default — success transition, no output
Result()

# with output data
Result(output={"user_id": 42, "created_at": "2025-01-15"})

# custom transition
Result(output={}, transition="needs_review")

# decision outcome
Result(transition="true")
```

---

## NodeError

A failed node outcome.

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `code` | `str` | required | Machine-readable error code |
| `message` | `str` | required | Human-readable description |
| `details` | `dict[str, Any]` | `{}` | Structured context — field errors, IDs, etc. |
| `transition` | `str` | `"failure"` | Key used to select the next state |

### Examples

```python
# validation error with per-field details
NodeError(
    code="VALIDATION_ERROR",
    message="Input validation failed",
    details={"age": "must be >= 0", "role": "must be one of ['admin', 'user']"},
)

# HTTP error
NodeError(
    code="HTTP_ERROR",
    message="HTTP 404",
    details={"status_code": 404, "url": "https://api.example.com/user/99"},
)

# custom transition routing
NodeError(
    code="PAYMENT_DECLINED",
    message="Card was declined",
    details={"reason": "insufficient_funds"},
    transition="declined",   # routes to "declined" state, not "failure"
)
```

---

## How the runtime uses them

```python
result = await node.run(context, params)

# runtime reads the transition key from either type
next_node = node_def.transitions[result.transition]

# only Result carries output — NodeError output is ignored
if isinstance(result, Result):
    context = context.merge(result.output)
```

`NodeError` routes through the state machine exactly like `Result`. It does not terminate the workflow unless the `"failure"` transition leads to a terminal node.
