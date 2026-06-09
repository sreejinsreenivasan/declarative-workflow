# FastAPI Integration

Mount workflows to a FastAPI application with two routers: `api_router` for JSON APIs and `ui_router` for HTML forms.

## Installation

```bash
pip install 'workflow-core[fastapi]'
```

## API Router

Expose workflows as JSON endpoints.

```python
from fastapi import FastAPI
from workflow_core import Runtime, Workflow, Node, Registry
from workflow_core.nodes import FormNode, ResponseNode
from workflow_core.adapters.fastapi import api_router

workflow = Workflow(
    id="create_user",
    start="validate",
    nodes={
        "validate": Node(
            type="form",
            params={"fields": {"name": {"type": "str"}}},
            transitions={"success": "respond", "failure": "respond"},
        ),
        "respond": Node(type="response", transitions={"success": None}),
    },
)

registry = Registry()
registry.register("form")(FormNode)
registry.register("response")(ResponseNode)

runtime = Runtime(workflow, registry)

app = FastAPI()
app.include_router(api_router(runtime))
```

Routes:

| Method | Path | Behavior |
|--------|------|----------|
| `POST` | `/execute` | Auto-generate `execution_id` |
| `POST` | `/execute/{execution_id}` | Use specific `execution_id` |

Both accept JSON body and return JSON response with the workflow result.

```bash
# Start execution with auto-generated ID
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice"}'

# Start with specific execution ID
curl -X POST http://localhost:8000/execute/user-123 \
  -H "Content-Type: application/json" \
  -d '{"name": "Bob"}'
```

## UI Router

Mount workflows as server-side-rendered forms with HTMX support.

```python
from workflow_core import InMemoryStore
from workflow_core.adapters.fastapi import ui_router

store = InMemoryStore()
runtime = Runtime(workflow, registry, store=store)

app.include_router(ui_router(runtime, prefix="/forms"))
```

Routes:

| Method | Path | Behavior |
|--------|------|----------|
| `GET` | `/forms/new` | Start fresh execution, render first form |
| `GET` | `/{execution_id}` | Resume execution, render current step |
| `POST` | `/{execution_id}` | Submit form data, advance workflow |

### Form Flow

1. **GET /forms/new** — Create new execution, render initial form
2. **POST /{execution_id}** — Submit form data
   - If validation fails → re-render with errors
   - If validation passes → advance to next node
3. **GET /{execution_id}** — Resume suspended execution (after POST, before next interaction)

### Templates

Use Jinja2 templates with the `UINode`:

```python
import jinja2

env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))

workflow = Workflow(
    id="signup",
    start="collect",
    nodes={
        "collect": Node(
            type="ui",
            params={
                "template": "form.html",
                "partial_template": "_form.html",  # For HTMX
                "fields": {
                    "email": {"type": "str", "required": True},
                    "age": {"type": "int", "required": True, "min": 18},
                },
            },
            transitions={"render": None, "submitted": "confirm", "error": None},
        ),
        "confirm": Node(type="response", transitions={"success": None}),
    },
)

registry.register("ui")(lambda: UINode(env))
```

Template variables:

| Variable | Type | Description |
|----------|------|-------------|
| `data` | dict | Current execution context data |
| `fields` | dict | Field schema from node params |
| `errors` | dict | Validation errors (key → message) |
| `execution_id` | str | Current execution ID |
| `node` | str | Current node ID |

**form.html** (full page):

```html
<!DOCTYPE html>
<html>
<body>
  <form action="/forms/{{ execution_id }}" method="post" hx-boost="true">
    {% for name, schema in fields.items() %}
      <label>{{ name }}</label>
      <input type="text" name="{{ name }}" required />
      {% if errors[name] %}<p class="error">{{ errors[name] }}</p>{% endif %}
    {% endfor %}
    <button type="submit">Next</button>
  </form>
</body>
</html>
```

**_form.html** (HTMX partial):

```html
<div id="form">
  {% for name, schema in fields.items() %}
    <div class="field">
      <label>{{ name }}</label>
      <input type="text" name="{{ name }}" required />
      {% if errors[name] %}<p class="error">{{ errors[name] }}</p>{% endif %}
    </div>
  {% endfor %}
  <button type="submit" hx-post="/forms/{{ execution_id }}">Next</button>
</div>
```

### Form Data Types

HTML forms submit all data as strings. The adapter automatically coerces values to expected types:

| Schema Type | Input String | Coerced Value |
|-------------|--------------|---------------|
| `"int"` | `"30"` | `30` |
| `"float"` | `"3.14"` | `3.14` |
| `"bool"` | `"true"` | `True` |
| `"str"` | `"hello"` | `"hello"` |

Invalid coercions fail validation (e.g., `"abc"` → int fails type check).

## Execution Persistence

Both routers support persistence for suspend/resume workflows:

```python
from workflow_core import InMemoryStore

store = InMemoryStore()  # Development only
runtime = Runtime(workflow, registry, store=store)
```

For production, use Redis:

```python
# (not yet implemented)
# from workflow_core.adapters.redis import RedisStore
# store = RedisStore(redis_client)
```

The runtime suspends on transitions in the default `suspend_on` set: `{"render", "error"}`. Suspended executions are saved to the store and can be resumed later.

## Error Handling

Missing execution ID returns 404:

```json
{
  "error": "Execution 'unknown-id' not found",
  "status_code": 404
}
```

Validation errors render the form with error messages:

```html
<!-- re-rendered with errors dict populated -->
<p class="error">age: must be >= 18</p>
```

## Full Example

```python
from fastapi import FastAPI
import jinja2
from workflow_core import (
    Workflow, Node, Registry, Runtime, InMemoryStore,
)
from workflow_core.nodes import FormNode, ResponseNode
from workflow_core.nodes.ui import UINode
from workflow_core.adapters.fastapi import api_router, ui_router

# Define workflow
workflow = Workflow(
    id="signup",
    start="form",
    nodes={
        "form": Node(
            type="ui",
            params={
                "template": "form.html",
                "fields": {
                    "name": {"type": "str", "required": True},
                    "age": {"type": "int", "required": True, "min": 18},
                },
            },
            transitions={"render": None, "submitted": "done", "error": None},
        ),
        "done": Node(
            type="response",
            params={"status": 200},
            transitions={"success": None},
        ),
    },
)

# Register nodes
registry = Registry()
env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))
registry.register("ui")(lambda: UINode(env))
registry.register("response")(ResponseNode)

# Create runtime and app
store = InMemoryStore()
runtime = Runtime(workflow, registry, store=store)

app = FastAPI()
app.include_router(api_router(runtime, prefix="/api"))
app.include_router(ui_router(runtime, prefix="/ui"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Then visit `http://localhost:8000/ui/new` to start a workflow.
