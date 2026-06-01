# ResponseNode

Shapes the final API response from `context.data`. Typically the terminal node in every workflow path.

```python
from workflow_core.nodes import ResponseNode
registry.register("response")(ResponseNode)
```

---

## Params

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `status` | `int` | `200` | HTTP status code |
| `include` | `list[str] \| None` | `None` | Keys to include from `context.data`. `None` includes everything |

---

## Transitions

| Key | When |
|-----|------|
| `"success"` | Always |

`ResponseNode` always succeeds. Use the workflow's terminal transition (`None`) after it.

---

## Output

```python
Result(output={"response": {"data": {...}, "status": 200}})
```

The framework adapter reads `context.data["response"]` to build the HTTP response.

---

## Examples

```python
# success — include only specific fields
Node(
    type="response",
    params={"status": 201, "include": ["validated"]},
    transitions={"success": None},
)

# error — empty body
Node(
    type="response",
    params={"status": 409},
    transitions={"success": None},
)

# include everything in context
Node(
    type="response",
    params={"status": 200},
    transitions={"success": None},
)
```

---

## Reading the response

After execution:

```python
context = await runtime.execute("exec_001", input_data={...})
response = context.data["response"]
# {"data": {...}, "status": 201}
```
