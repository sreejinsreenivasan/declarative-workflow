# DecisionNode

Evaluates a condition against `context.data` and routes to a branch.

```python
from workflow_core.nodes import DecisionNode
registry.register("decision")(DecisionNode)
```

---

## Params

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `key` | `str` | required | Key to read from `context.data` |
| `operator` | `str` | `"eq"` | Comparison operator |
| `value` | `Any` | `None` | Value to compare against |

### Operators

| Operator | Condition |
|----------|-----------|
| `eq` | `actual == value` |
| `neq` | `actual != value` |
| `gt` | `actual > value` |
| `gte` | `actual >= value` |
| `lt` | `actual < value` |
| `lte` | `actual <= value` |
| `in` | `actual in value` |
| `not_in` | `actual not in value` |
| `exists` | `actual is not None` |
| `not_exists` | `actual is None` |

---

## Transitions

| Key | When |
|-----|------|
| `"true"` | Condition matched |
| `"false"` | Condition did not match |
| `"failure"` | Invalid params (missing `key`, unknown `operator`) |

---

## Examples

```python
# check string equality
Node(
    type="decision",
    params={"key": "kyc_status", "operator": "eq", "value": "approved"},
    transitions={"true": "create_account", "false": "reject"},
)

# check numeric threshold
Node(
    type="decision",
    params={"key": "score", "operator": "gte", "value": 700},
    transitions={"true": "approve_loan", "false": "manual_review"},
)

# check membership
Node(
    type="decision",
    params={"key": "role", "operator": "in", "value": ["admin", "superuser"]},
    transitions={"true": "admin_flow", "false": "user_flow"},
)

# check existence
Node(
    type="decision",
    params={"key": "existing_user", "operator": "exists"},
    transitions={"true": "conflict_response", "false": "create_user"},
)
```
