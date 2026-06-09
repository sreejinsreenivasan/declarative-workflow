# Django Integration

Mount workflows to a Django application with two decorators: `json_api_view` for JSON APIs and `form_view` for HTML forms.

## Installation

```bash
pip install 'workflow-core[django]'
```

## JSON API View

Expose workflows as JSON endpoints.

```python
from django.urls import path
from workflow_core import Runtime, Workflow, Node, Registry
from workflow_core.nodes import FormNode, ResponseNode
from workflow_core.adapters.django import json_api_view

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

@json_api_view(runtime)
def create_user(request):
    """This decorator handles GET and POST automatically."""
    pass

urlpatterns = [
    path("api/users/", create_user),
]
```

Routes:

| Method | Query | Behavior |
|--------|-------|----------|
| `POST` | (none) | Auto-generate `execution_id` |
| `POST` | `execution_id=xyz` | Use specific `execution_id` |
| `GET` | `execution_id=xyz` | Resume execution by ID |

Both POST routes accept form data and return JSON response with the workflow result.

```bash
# Start with auto-generated ID
curl -X POST http://localhost:8000/api/users/ \
  -d 'name=Alice'

# Start with specific ID
curl -X POST http://localhost:8000/api/users/?execution_id=user-123 \
  -d 'name=Bob'

# Resume execution
curl -X GET 'http://localhost:8000/api/users/?execution_id=user-123'
```

## Form View

Mount workflows as server-side-rendered forms.

```python
from django.urls import path
from workflow_core import InMemoryStore
from workflow_core.adapters.django import form_view

store = InMemoryStore()
runtime = Runtime(workflow, registry, store=store)

@form_view(runtime)
def signup(request):
    """GET renders form, POST submits form."""
    pass

urlpatterns = [
    path("signup/", signup),
]
```

Routes:

| Method | Query | Behavior |
|--------|-------|----------|
| `GET` | (none) | Start fresh execution, render first form |
| `GET` | `execution_id=xyz` | Resume execution, render current step |
| `POST` | `execution_id=xyz` | Submit form data, advance workflow |

### Form Flow

1. **GET /signup/** — Create new execution, render initial form
2. **POST /signup/?execution_id=xyz** — Submit form data
   - If validation fails → re-render with error messages
   - If validation passes → advance to next node
3. **GET /signup/?execution_id=xyz** — Resume suspended execution

### Templates with Jinja2

Use Jinja2 to render forms with `UINode`:

```python
import jinja2
from workflow_core.nodes.ui import UINode

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

Template variables available:

| Variable | Type | Description |
|----------|------|-------------|
| `data` | dict | Current execution context |
| `fields` | dict | Field schema from node params |
| `errors` | dict | Validation errors (field → message) |
| `execution_id` | str | Current execution ID |
| `node` | str | Current node ID |

**form.html** (full page):

```html
<!DOCTYPE html>
<html>
<body>
  <h1>Sign Up</h1>
  <form method="post" action="/signup/">
    <!-- execution_id -->
    {% csrf_token %}
    
    {% for name in fields %}
      <div class="field">
        <label for="{{ name }}">{{ name }}</label>
        <input type="text" id="{{ name }}" name="{{ name }}" required />
        {% if errors[name] %}
          <p class="error">{{ errors[name] }}</p>
        {% endif %}
      </div>
    {% endfor %}
    
    <button type="submit">Next</button>
  </form>
</body>
</html>
```

**_form.html** (HTMX partial):

```html
<div id="form" hx-boost="true">
  {% for name in fields %}
    <div class="field">
      <label for="{{ name }}">{{ name }}</label>
      <input type="text" id="{{ name }}" name="{{ name }}" required />
      {% if errors[name] %}
        <p class="error">{{ errors[name] }}</p>
      {% endif %}
    </div>
  {% endfor %}
  <button type="submit" hx-post="/signup/?execution_id={{ execution_id }}">Next</button>
</div>
```

**Injecting execution_id:**

The `<!-- execution_id -->` placeholder is replaced with a hidden input:

```python
from workflow_core.adapters.django import add_execution_id_to_form

html = render_to_string("form.html", context)
html = add_execution_id_to_form(html, execution_id)
response = HttpResponse(html)
```

Or in templates directly:

```django
<input type="hidden" name="execution_id" value="{{ execution_id }}" />
```

### Form Data Types

HTML forms submit all data as strings. The adapter automatically coerces values:

| Schema Type | Input String | Coerced Value |
|-------------|--------------|---------------|
| `"int"` | `"30"` | `30` |
| `"float"` | `"3.14"` | `3.14` |
| `"bool"` | `"true"` | `True` |
| `"str"` | `"hello"` | `"hello"` |

Invalid coercions fail validation (e.g., `"abc"` as int fails type check).

## Execution Persistence

Both views support persistence for suspend/resume workflows:

```python
from workflow_core import InMemoryStore

store = InMemoryStore()  # Development only
runtime = Runtime(workflow, registry, store=store)
```

For production, use a custom store (Redis, database, etc.):

```python
class MyStore:
    async def save(self, execution_id: str, context: Context) -> None:
        # Save context to database
        
    async def load(self, execution_id: str) -> Context | None:
        # Load context from database
```

The runtime suspends on transitions in the default `suspend_on` set: `{"render", "error"}`. Suspended executions are saved to the store.

## CSRF Protection

Both decorators disable CSRF for simplicity. In production, add CSRF tokens to forms:

```python
{% csrf_token %}
```

And enable CSRF verification:

```python
from django.views.decorators.csrf import csrf_protect

@csrf_protect
@form_view(runtime)
def signup(request):
    pass
```

## Full Example

**urls.py:**

```python
from django.urls import path
import jinja2
from workflow_core import (
    Workflow, Node, Registry, Runtime, InMemoryStore,
)
from workflow_core.nodes import FormNode, ResponseNode
from workflow_core.nodes.ui import UINode
from workflow_core.adapters.django import json_api_view, form_view

# Workflow
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

# Registry
env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))
registry = Registry()
registry.register("ui")(lambda: UINode(env))
registry.register("response")(ResponseNode)

# Runtime
store = InMemoryStore()
runtime = Runtime(workflow, registry, store=store)

# Views
@json_api_view(runtime)
def api_signup(request):
    pass

@form_view(runtime)
def form_signup(request):
    pass

# URLs
urlpatterns = [
    path("api/signup/", api_signup),
    path("signup/", form_signup),
]
```

Then visit `http://localhost:8000/signup/` to start a workflow.
