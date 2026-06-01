# FormNode

Validates user-supplied input against a field schema.

```python
from workflow_core.nodes import FormNode
registry.register("form")(FormNode)
```

---

## Params

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `fields` | `dict[str, FieldRules]` | `{}` | Field definitions to validate |
| `source` | `str` | `"input"` | Key in `context.data` where input data lives |

### FieldRules

| Key | Type | Description |
|-----|------|-------------|
| `required` | `bool` | Whether the field must be present. Default `True` |
| `type` | `str` | `"str"`, `"int"`, `"float"`, `"bool"` |
| `min` | `int \| float` | Minimum value (int/float only) |
| `max` | `int \| float` | Maximum value (int/float only) |
| `min_length` | `int` | Minimum string length (str only) |
| `max_length` | `int` | Maximum string length (str only) |
| `enum` | `list` | Allowed values |

---

## Transitions

| Key | When |
|-----|------|
| `"success"` | All fields pass validation |
| `"failure"` | One or more fields fail validation |

---

## Output (on success)

```python
Result(output={"validated": {"name": "Alice", "age": 30, "role": "admin"}})
```

Only fields defined in `fields` are included in `validated`.

## Output (on failure)

```python
NodeError(
    code="VALIDATION_ERROR",
    message="Validation failed",
    details={"age": "must be >= 0", "role": "must be one of ['admin', 'user']"},
)
```

All failing fields are reported in a single `NodeError`.

---

## Example

```python
Node(
    type="form",
    params={
        "source": "input",
        "fields": {
            "name": {"type": "str", "required": True, "max_length": 100},
            "age":  {"type": "int", "required": True, "min": 0, "max": 150},
            "role": {"type": "str", "required": True, "enum": ["admin", "user"]},
        },
    },
    transitions={"success": "next_step", "failure": "handle_error"},
)
```
