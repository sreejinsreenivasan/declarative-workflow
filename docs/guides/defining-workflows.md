# Defining Workflows

## Workflow

A `Workflow` defines the complete state machine — every node, every transition, and the starting point.

```python
from workflow_core import Workflow, Node

workflow = Workflow(
    id="onboarding",        # unique identifier
    start="collect_info",   # first node to execute
    nodes={
        "collect_info": Node(...),
        "verify_kyc":   Node(...),
        "create_account": Node(...),
    },
)
```

### Validation at construction

`Workflow` validates its definition immediately on construction — before any execution.

- `start` must exist in `nodes`
- Every non-`None` transition target must exist in `nodes`

```python
# raises ValueError: start node 'missing' not in nodes
Workflow(id="w", start="missing", nodes={"step": Node(type="form")})

# raises ValueError: node 'a' transition 'success' → unknown node 'nowhere'
Workflow(
    id="w",
    start="a",
    nodes={"a": Node(type="form", transitions={"success": "nowhere"})},
)
```

---

## Node

A `Node` is a state in the workflow. It has three fields:

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | Matches a registered node class in the `Registry` |
| `params` | `dict` | Static configuration passed to the node's `run()` method |
| `transitions` | `dict[str, str \| None]` | Maps outcome keys to next node ids |

```python
Node(
    type="form",
    params={
        "fields": {
            "email": {"type": "str", "required": True},
        }
    },
    transitions={
        "success": "next_step",
        "failure": "handle_error",
    },
)
```

### Terminal transitions

A transition value of `None` ends the workflow at that state:

```python
transitions={"success": None}
```

### Multiple outcomes

A node can have as many transition keys as needed. `DecisionNode` always returns `"true"` or `"false"`. `HTTPNode` returns `"success"` or `"failure"`. Custom nodes return whatever outcome key they declare.

```python
Node(
    type="decision",
    params={"key": "score", "operator": "gte", "value": 700},
    transitions={
        "true":  "approve",
        "false": "manual_review",
    },
)
```

---

## Common patterns

### Linear flow

```python
nodes={
    "a": Node(type="form",     transitions={"success": "b", "failure": "error"}),
    "b": Node(type="http",     transitions={"success": "c", "failure": "error"}),
    "c": Node(type="response", transitions={"success": None}),
    "error": Node(type="response", params={"status": 422}, transitions={"success": None}),
}
```

### Decision branch

```python
nodes={
    "check_age": Node(
        type="decision",
        params={"key": "age", "operator": "gte", "value": 18},
        transitions={"true": "adult_flow", "false": "minor_flow"},
    ),
    "adult_flow": Node(type="response", params={"status": 200}, transitions={"success": None}),
    "minor_flow": Node(type="response", params={"status": 403}, transitions={"success": None}),
}
```

### Error recovery

Route `NodeError` failures to a recovery state instead of ending:

```python
nodes={
    "call_api": Node(
        type="http",
        params={"method": "POST", "url": "https://kyc.example.com"},
        transitions={
            "success": "save_result",
            "failure": "flag_for_review",   # NodeError routes here
        },
    ),
    "save_result":      Node(type="persist",  transitions={"success": None}),
    "flag_for_review":  Node(type="response", params={"status": 202}, transitions={"success": None}),
}
```

---

## Input data

Pass input data when calling `runtime.execute()`. It becomes available in `context.data`:

```python
context = await runtime.execute(
    execution_id="exec_001",
    input_data={"input": {"name": "Alice", "age": 30}},
)
```

`FormNode` reads from `context.data["input"]` by default. Use `params.source` to change the key:

```python
Node(type="form", params={"source": "body", "fields": {...}})
```
