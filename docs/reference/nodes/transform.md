# TransformNode

Maps and reshapes `context.data` fields using dot-path notation. Pure transformation — no I/O.

```python
from workflow_core.nodes import TransformNode
registry.register("transform")(TransformNode)
```

---

## Params

| Key | Type | Description |
|-----|------|-------------|
| `mapping` | `dict[str, str]` | `{target_key: source_path}` — required, must be non-empty |

### Dot-path notation

Source paths resolve nested keys using `.` as separator:

| Path | Resolves to |
|------|-------------|
| `"name"` | `context.data["name"]` |
| `"validated.name"` | `context.data["validated"]["name"]` |
| `"kyc_result.identity.score"` | `context.data["kyc_result"]["identity"]["score"]` |

If a path does not resolve (key missing or intermediate is not a dict), that key is omitted from the output — no error.

---

## Transitions

| Key | When |
|-----|------|
| `"success"` | Mapping applied (even if some paths were missing) |
| `"failure"` | `mapping` is empty or missing from params |

---

## Output

```python
Result(output={"user_name": "Alice", "user_age": 30})
```

Only keys that resolved successfully are included.

---

## Examples

```python
# rename and flatten nested fields
Node(
    type="transform",
    params={
        "mapping": {
            "user_name":  "validated.name",
            "user_age":   "validated.age",
            "kyc_status": "kyc_result.status",
        }
    },
    transitions={"success": "persist_user", "failure": "error"},
)

# project top-level fields
Node(
    type="transform",
    params={
        "mapping": {
            "display_name": "name",
            "score":        "credit_score",
        }
    },
    transitions={"success": "respond"},
)
```
