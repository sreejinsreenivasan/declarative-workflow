# Workflow & Node

## Workflow

```python
from workflow_core import Workflow, Node
```

Defines the complete state machine. Immutable after construction.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique workflow identifier |
| `start` | `str` | ID of the first node to execute |
| `nodes` | `dict[str, Node]` | All states in the workflow |

### Validation

Raises `ValidationError` at construction if:
- `start` is not a key in `nodes`
- Any `transitions` value (non-`None`) is not a key in `nodes`

### Example

```python
workflow = Workflow(
    id="user_onboarding",
    start="collect_info",
    nodes={
        "collect_info": Node(
            type="form",
            params={"fields": {"name": {"type": "str"}}},
            transitions={"success": "respond", "failure": "respond"},
        ),
        "respond": Node(
            type="response",
            transitions={"success": None},
        ),
    },
)
```

---

## Node

A single state in the workflow.

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | `str` | required | Maps to a registered node class in `Registry` |
| `params` | `dict[str, Any]` | `{}` | Static config passed to `node.run()` |
| `transitions` | `dict[str, str \| None]` | `{}` | Outcome key → next node id (or `None` to end) |

### Example

```python
Node(
    type="http",
    params={
        "method": "POST",
        "url": "https://api.example.com/verify",
        "body_key": "validated",
        "response_key": "verify_result",
    },
    transitions={
        "success": "next_step",
        "failure": "error_handler",
    },
)
```

### Terminal node

```python
Node(type="response", transitions={"success": None})
```

A transition of `None` ends the workflow. The runtime exits the execution loop and returns the current context.
