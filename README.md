# workflow-core

A declarative, pipeline-based workflow runtime for Python web servers.

Replace tightly-coupled view layers with explicit, testable, declarative node-based workflows. Define your business logic once, reuse it everywhere.

```python
from workflow_core import Workflow, Node, Runtime, Registry

# Define workflow
workflow = Workflow(
    id="create_user",
    start="validate",
    nodes={
        "validate": Node(type="form", params={...}, transitions={...}),
        "save": Node(type="persist", params={...}, transitions={...}),
        "respond": Node(type="response", params={...}, transitions={...}),
    },
)

# Register node types
registry = Registry()
registry.register("form")(FormNode)
registry.register("persist")(PersistNode(db))
registry.register("response")(ResponseNode)

# Execute
runtime = Runtime(workflow, registry)
context = await runtime.execute("exec-1", input_data={"input": {...}})
```

## Features

- **Declarative** — Define workflows in Python with Pydantic schemas
- **State machine execution** — Explicit transitions between nodes, not DAGs
- **Suspend/resume** — Multi-request workflows (forms, confirmations, async tasks)
- **Processor-based composition** — Reusable async functions with `pipe()`
- **Built-in nodes** — Form validation, HTTP calls, persistence, SSR rendering
- **Custom nodes** — Extend with your own business logic
- **Observability** — Event emission at every execution boundary
- **Framework-agnostic core** — Use with FastAPI, Django, or any framework
- **Immutable state** — Frozen Pydantic models, pure transformations
- **Type-safe** — Full mypy strict mode compliance

## Quick Start

### Installation

```bash
# Core library
pip install workflow-core

# With FastAPI support
pip install 'workflow-core[fastapi]'
```

### FastAPI Example

```python
from fastapi import FastAPI
from workflow_core import Runtime, Workflow, Node, Registry
from workflow_core.nodes import FormNode, ResponseNode
from workflow_core.adapters.fastapi import api_router

# Define workflow
workflow = Workflow(
    id="signup",
    start="collect",
    nodes={
        "collect": Node(type="form", params={"fields": {...}}),
        "respond": Node(type="response", params={"status": 201}),
    },
)

# Set up
registry = Registry()
registry.register("form")(FormNode)
registry.register("response")(ResponseNode)
runtime = Runtime(workflow, registry)

# Mount to FastAPI
app = FastAPI()
app.include_router(api_router(runtime, prefix="/api"))

# Usage: POST /api/execute with JSON body
```

### HTML Forms with Suspend/Resume

```python
import jinja2
from workflow_core import InMemoryStore
from workflow_core.nodes.ui import UINode
from workflow_core.adapters.fastapi import ui_router

env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))

workflow = Workflow(
    id="form_flow",
    start="step1",
    nodes={
        "step1": Node(
            type="ui",
            params={"template": "form.html", "fields": {...}},
            transitions={"render": None, "submitted": "done", "error": None},
        ),
        "done": Node(type="response", transitions={"success": None}),
    },
)

registry.register("ui")(lambda: UINode(env))
store = InMemoryStore()
runtime = Runtime(workflow, registry, store=store)

app.include_router(ui_router(runtime, prefix="/forms"))

# Usage:
# GET  /forms/new               → render form
# POST /forms/{execution_id}    → submit form, advance workflow
```

## Architecture

```
src/workflow_core/
  ├── entities/        Domain models (Workflow, Context, Result)
  ├── execution/       Execution orchestration (Runtime, state transitions)
  ├── nodes/           Built-in nodes (form, http, persist, response, ui)
  ├── processors.py    Reusable async processors (validation, HTTP, mapping)
  └── adapters/        Framework integrations (FastAPI)
```

**Layer boundary** (enforced):
- `adapters/` → `nodes/` → `entities/` + `execution/`

Core layers import only stdlib + Pydantic. Framework dependencies isolated to adapters.

## Built-In Nodes

| Node | Purpose |
|------|---------|
| `FormNode` | Validate input fields (type, required, min/max, enum) |
| `DecisionNode` | Branch on conditions (eq, neq, gt, lt, in, exists) |
| `HTTPNode` | Make async HTTP requests |
| `TransformNode` | Map/filter context fields |
| `PersistNode` | Read/write to storage (database, cache, etc.) |
| `ResponseNode` | Format final HTTP response |
| `UINode` | Render Jinja2 templates + form validation (HTMX-aware) |

## Processors

Processors are pure async functions for composing business logic:

```python
from workflow_core import pipe, validate_fields, call_http, write_record

# Reusable processors
validate = validate_fields({"email": {...}, "password": {...}})
http = call_http("POST", "https://api.example.com/verify", body_key="validated")
persist = write_record(db, "users:{email}")

# Compose into pipeline
pipeline = pipe(validate, http, persist)

# Use in custom node
class SignupNode:
    async def run(self, context, params):
        result = await pipeline(context)
        if isinstance(result, NodeError):
            return result
        return Result(output=result.data, transition="success")
```

## Examples

### Create User Workflow

```python
workflow = Workflow(
    id="create_user",
    start="collect",
    nodes={
        "collect": Node(
            type="form",
            params={"fields": {"name": {...}, "age": {...}}},
            transitions={"success": "check_duplicate", "failure": "error"},
        ),
        "check_duplicate": Node(
            type="http",
            params={"method": "POST", "url": "...", "body_key": "validated"},
            transitions={"success": "save", "failure": "error"},
        ),
        "save": Node(type="persist", params={...}),
        "error": Node(type="response", params={"status": 400}),
    },
)
```

### KYC Verification (DRF)

```python
# See examples/drf_kyc_api.py for complete implementation
# Form validation → API call → decision → response
```

## Documentation

- **[Getting Started](docs/getting-started.md)** — Installation, first workflow
- **[Concepts](docs/concepts.md)** — State machines, context, processors
- **[Guides](docs/):**
  - [Defining Workflows](docs/guides/defining-workflows.md)
  - [Custom Nodes](docs/guides/custom-nodes.md)
  - [FastAPI Integration](docs/guides/fastapi-integration.md)
  - [Django + DRF Patterns](docs/guides/django-drf-integration.md)
  - [Error Handling](docs/guides/error-handling.md)
  - [Events & Observability](docs/guides/events.md)
- **[API Reference](docs/reference/)** — All classes, functions, node types
- **[Examples](examples/)** — User creation, KYC verification

## Testing

```bash
# Install dev dependencies
pip install -e '.[fastapi]'
poetry install --with dev

# Run tests
poetry run pytest

# With coverage
poetry run pytest --cov=workflow_core --cov-report=term-missing

# Current: 189 tests passing, 98% coverage
```

## Philosophy

1. **Declarative over imperative** — Define workflows as data, not code
2. **Immutable state** — Pure functions, predictable execution
3. **Framework-agnostic core** — Use with any Python web framework
4. **Composable processors** — Reuse validation, HTTP, mapping logic
5. **Explicit over implicit** — Transitions, error handling, state persistence

## Design Decisions

- **No DAGs** — State machines with explicit transitions are clearer for business workflows
- **Frozen Pydantic models** — Immutability prevents subtle bugs
- **Async-first** — All I/O is async; pure logic is sync
- **No automagic** — Transitions, storage, error handling are explicit
- **Typed results** — Workflows return `Result | NodeError`, never raise

## Stack

| Tool | Purpose |
|------|---------|
| Python 3.11+ | Language floor |
| Pydantic v2 | Schemas, validation, domain models |
| httpx | Async HTTP client |
| Jinja2 | Template rendering (optional) |
| FastAPI | Reference adapter |
| pytest | Test runner |
| mypy | Type checking (strict mode) |

## Contributing

Contributions welcome. See [CLAUDE.md](CLAUDE.md) for:
- Architecture rules
- Code style guidelines
- Testing requirements
- Commit message format
- Release process

## License

MIT

## Status

**Production-ready** — 189 tests, 98% coverage, solid architecture.

Suitable for:
- User registration workflows
- KYC/AML verification processes
- Multi-step form submissions
- Complex approval chains
- Any state-machine-based business process

Not suitable for:
- Simple CRUD endpoints (use FastAPI directly)
- Real-time systems requiring sub-millisecond latency
- DAG-style parallel task orchestration (use Celery/Dask)
