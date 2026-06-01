# UINode

Server-side rendering node with HTMX support. Combines form definition and template rendering into a single declaration. Handles GET (render) and POST (validate + transition) in one node.

```python
from workflow_core.nodes import UINode
import jinja2

env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))
registry.register("ui")(lambda: UINode(env))
```

---

## Params

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `template` | `str` | required | Template path relative to the Jinja2 environment loader |
| `partial_template` | `str` | — | Template used instead of `template` when `request.is_htmx` is `True` |
| `fields` | `dict[str, FieldRules]` | `{}` | Field definitions — same schema as `FormNode` |
| `source` | `str` | `"input"` | `context.data` key where POST input data lives |

See [FormNode](form.md) for the full `FieldRules` schema.

---

## Request context

The node reads `context.data["request"]` to determine how to behave:

| Key | Type | Description |
|-----|------|-------------|
| `method` | `str` | `"GET"` or `"POST"`. Defaults to `"GET"` if absent |
| `is_htmx` | `bool` | `True` if `HX-Request` header is present |

The FastAPI adapter populates this before calling `runtime.execute()`:

```python
input_data={
    "request": {
        "method": request.method,
        "is_htmx": "HX-Request" in request.headers,
    },
    "input": await request.form(),
}
```

---

## Transitions

| Key | When |
|-----|------|
| `"render"` | GET — template rendered successfully |
| `"submitted"` | POST — all fields passed validation |
| `"error"` | POST — one or more fields failed validation; template re-rendered with errors |
| `"failure"` | Template not found or missing `template` param |

---

## Template variables

Every template receives:

| Variable | Type | Description |
|----------|------|-------------|
| `data` | `dict` | Full `context.data` — all accumulated execution state |
| `fields` | `dict` | Field definitions from `params.fields` |
| `errors` | `dict[str, str]` | Per-field error messages. Empty on GET |
| `execution_id` | `str` | For use in form `action` URL |
| `node` | `str` | Current node id |

---

## Example template

```html
{# templates/onboarding/_step1.html — HTMX partial #}
<form hx-post="/workflow/{{ execution_id }}/{{ node }}"
      hx-target="#content"
      hx-swap="innerHTML">

    {% for name, field in fields.items() %}
    <div class="field {% if errors.get(name) %}has-error{% endif %}">
        <label for="{{ name }}">{{ field.get('label', name) }}</label>
        <input
            id="{{ name }}"
            name="{{ name }}"
            type="{{ 'number' if field.type == 'int' else 'text' }}"
            value="{{ data.get(name, '') }}"
        />
        {% if errors.get(name) %}
        <p class="error">{{ errors[name] }}</p>
        {% endif %}
    </div>
    {% endfor %}

    <button type="submit">Continue</button>
</form>
```

---

## Workflow example — multi-step onboarding

```python
Workflow(
    id="onboarding",
    start="step1",
    nodes={
        "step1": Node(
            type="ui",
            params={
                "template":         "onboarding/step1.html",
                "partial_template": "onboarding/_step1.html",
                "fields": {
                    "name":  {"type": "str", "required": True, "label": "Full Name"},
                    "email": {"type": "str", "required": True, "label": "Email"},
                },
            },
            transitions={
                "render":    None,
                "submitted": "step2",
                "error":     None,
            },
        ),
        "step2": Node(
            type="ui",
            params={
                "template":         "onboarding/step2.html",
                "partial_template": "onboarding/_step2.html",
                "fields": {
                    "age":  {"type": "int", "required": True, "min": 18, "label": "Age"},
                    "role": {"type": "str", "required": True,
                             "enum": ["admin", "user"], "label": "Role"},
                },
            },
            transitions={
                "render":    None,
                "submitted": "save",
                "error":     None,
            },
        ),
        "save": Node(
            type="persist",
            params={"operation": "write", "key": "user:new"},
            transitions={"success": "done", "failure": "done"},
        ),
        "done": Node(
            type="ui",
            params={"template": "onboarding/success.html"},
            transitions={"render": None},
        ),
    },
)
```

---

## HTMX routing in FastAPI

```python
@router.api_route("/workflow/{execution_id}/{node_id}", methods=["GET", "POST"])
async def handle_ui_step(
    execution_id: str,
    node_id: str,
    request: Request,
):
    form_data = dict(await request.form()) if request.method == "POST" else {}

    context = await runtime.execute(
        execution_id=execution_id,
        input_data={
            "request": {
                "method": request.method,
                "is_htmx": "HX-Request" in request.headers,
            },
            "input": form_data,
        },
    )

    html = context.data.get("html", "")
    return HTMLResponse(content=html)
```
