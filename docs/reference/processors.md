# Processors

Processors are pure async functions that transform execution context. They are the building blocks for composing custom nodes.

## Type

```python
Processor = Callable[[Context], Awaitable[Context | NodeError]]
```

A processor receives a context, performs validation or transformation, and returns either an updated context or an error.

## pipe

Compose processors left-to-right with short-circuit on error.

```python
from workflow_core import pipe, validate_fields, call_http

pipeline = pipe(
    validate_fields({"email": {"type": "str"}}),
    call_http("POST", "https://api.example.com/verify", body_key="validated"),
)

result = await pipeline(context)
```

If any processor returns `NodeError`, the pipeline stops and returns that error. Otherwise, context flows through each processor in sequence.

## validate_fields

Validate and coerce form input fields.

```python
validate_fields(
    fields: dict[str, dict],
    source: str = "input",
) -> Processor
```

**Parameters:**

- `fields`: Schema defining field rules (type, required, min/max, enum, length)
- `source`: Key in context.data to read input from (default: `"input"`)

**Field Rules:**

```python
{
    "age": {
        "type": "int",           # str, int, float, bool
        "required": True,        # (default True)
        "min": 0,                # numeric only
        "max": 150,              # numeric only
        "min_length": 3,         # string only
        "max_length": 100,       # string only
        "enum": ["admin", "user"],  # whitelist values
    }
}
```

**Behavior:**

- Coerces string values to expected type (e.g., form `"30"` → int `30`)
- Returns `NodeError("VALIDATION_ERROR")` with per-field error messages if validation fails
- Merges `{"validated": {...}}` on success

**Example:**

```python
result = await validate_fields({
    "name": {"type": "str", "required": True},
    "age": {"type": "int", "min": 18},
})(context)

if isinstance(result, NodeError):
    return result  # validation failed

# result.data["validated"] = {"name": "Alice", "age": 30}
```

## check_condition

Evaluate a single condition against context data.

```python
check_condition(
    key: str,
    operator: str = "eq",
    value: Any = None,
) -> Processor
```

**Operators:**

| Operator | Behavior |
|----------|----------|
| `eq` | Equal |
| `neq` | Not equal |
| `gt` | Greater than |
| `gte` | Greater than or equal |
| `lt` | Less than |
| `lte` | Less than or equal |
| `in` | In list |
| `not_in` | Not in list |
| `exists` | Value is not None |
| `not_exists` | Value is None |

**Behavior:**

Merges `{"_matched": bool}` into context. Used by `DecisionNode` to choose transitions.

**Example:**

```python
result = await check_condition("status", "eq", "approved")(context)
# result.data["_matched"] = True or False
```

## call_http

Make an async HTTP request and merge response into context.

```python
call_http(
    method: str,
    url: str,
    body_key: str | None = None,
    response_key: str = "http_response",
    headers: dict[str, str] | None = None,
) -> Processor
```

**Behavior:**

- Reads request body from `context.data[body_key]` (if specified)
- Makes HTTP request, parses JSON response
- Merges `{response_key: response_json}` on success
- Returns `NodeError` on HTTP error (4xx/5xx) or connection error

**Example:**

```python
result = await call_http(
    method="POST",
    url="https://api.example.com/users",
    body_key="validated",
    response_key="user",
)(context)

if isinstance(result, NodeError):
    return result

# result.data["user"] = {...response JSON...}
```

## map_fields

Map fields using dot-path notation.

```python
map_fields(mapping: dict[str, str]) -> Processor
```

**Parameters:**

`mapping`: Dict of `{target: "source.path"}`. Uses dot notation to traverse nested objects.

**Behavior:**

- Reads values from `context.data` using source paths
- Merges mapped values into context
- Missing paths are silently excluded (no error)

**Example:**

```python
result = await map_fields({
    "user_id": "kyc.user_id",
    "risk_score": "kyc.result.risk_score",
})(context)

if "kyc.result.risk_score" exists in context, merges it as "risk_score"
```

## write_record

Write context data to a repository.

```python
write_record(
    repo: Repository,
    key: str,
    data_key: str = "validated",
) -> Processor
```

**Behavior:**

- Reads data from `context.data[data_key]`
- Calls `await repo.set(key, data)`
- Merges `{"persisted": True}` on success

## read_record

Read data from a repository.

```python
read_record(
    repo: Repository,
    key: str,
    output_key: str = "record",
) -> Processor
```

**Behavior:**

- Calls `await repo.get(key)`
- Returns `NodeError("NOT_FOUND")` if record not found
- Merges `{output_key: record_data}` on success

## delete_record

Delete a record from a repository.

```python
delete_record(repo: Repository, key: str) -> Processor
```

**Behavior:**

- Calls `await repo.delete(key)`
- Merges `{"deleted": True}` on success

## shape_response

Shape the final HTTP response.

```python
shape_response(
    include: list[str] | None = None,
    status: int = 200,
) -> Processor
```

**Behavior:**

- Filters context.data to only keys in `include` (if specified)
- Merges `{"response": {"data": {...}, "status": <code>}}`

**Example:**

```python
result = await shape_response(include=["user_id"], status=201)(context)

# result.data["response"] = {
#     "data": {"user_id": 123},
#     "status": 201
# }
```

## render_template

Render a Jinja2 template and merge HTML into context.

```python
render_template(
    env: jinja2.Environment,
    template: str,
    partial: str | None = None,
    fields: dict[str, Any] | None = None,
    errors: dict[str, str] | None = None,
) -> Processor
```

**Behavior:**

- If HTMX request and `partial` provided, renders `partial`
- Otherwise renders `template`
- Passes variables: `data`, `fields`, `errors`, `execution_id`, `node`
- Merges `{"html": rendered_html}` on success
- Returns `NodeError("TEMPLATE_NOT_FOUND")` if template missing

**Example:**

```python
env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))

result = await render_template(
    env,
    template="form.html",
    partial="_form.html",
    fields={"name": {}, "age": {}},
)(context)

# result.data["html"] = "...rendered HTML..."
```

## Composing Custom Processors

Create custom processors by implementing the `Processor` type:

```python
async def my_processor(context: Context) -> Context | NodeError:
    # Do something with context
    if error_condition:
        return NodeError(code="MY_ERROR", message="...")
    
    # Return modified context
    return context.merge({"my_key": "my_value"})
```

Then compose with `pipe`:

```python
result = await pipe(
    validate_fields(fields),
    my_processor,
    call_http("POST", url),
)(context)
```

## Error Handling

All processors either return a modified `Context` or a `NodeError`. The `pipe` combinator short-circuits on `NodeError`:

```python
result = await pipe(
    validate_fields(fields),  # fails, returns NodeError
    call_http(...),           # never runs
)(context)

assert isinstance(result, NodeError)
assert result.code == "VALIDATION_ERROR"
```

Nodes check the result type and decide how to handle errors:

```python
result = await my_processor(context)
if isinstance(result, NodeError):
    return result  # Return error to runtime
```
