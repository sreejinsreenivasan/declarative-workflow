# workflow-core

Declarative, pipeline-based workflow runtime for Python web servers.

Define business flows as state machines in Python. Mount them to FastAPI or Django. Replace tangled service layers with explicit, composable execution.

---

## The problem it solves

Traditional web applications scatter execution flow across controllers, serializers, services, ORM hooks, and async jobs. When something breaks, you trace through five layers to find where it happened. When something needs to change, you edit in six places.

`workflow-core` makes execution explicit. A workflow is a graph of named states. Each state runs a node. Each node returns an outcome. The runtime follows the transitions. The context carries all state.

```
form → decision → http → persist → response
```

You can read this. You can trace it. You can change it.

---

## Install

```bash
pip install workflow-core
```

---

## Quickstart

```python
import asyncio
from workflow_core import Workflow, Node, Runtime, Registry
from workflow_core.nodes import FormNode, DecisionNode, PersistNode, ResponseNode

# 1. Register node types
registry = Registry()
registry.register("form")(FormNode)
registry.register("decision")(DecisionNode)
registry.register("response")(ResponseNode)

# 2. Define the workflow
workflow = Workflow(
    id="create_user",
    start="collect",
    nodes={
        "collect": Node(
            type="form",
            params={
                "fields": {
                    "name": {"type": "str", "required": True},
                    "age":  {"type": "int",  "required": True, "min": 0},
                    "role": {"type": "str",  "required": True, "enum": ["admin", "user"]},
                }
            },
            transitions={"success": "respond_ok", "failure": "respond_error"},
        ),
        "respond_ok": Node(
            type="response",
            params={"include": ["validated"], "status": 201},
            transitions={"success": None},
        ),
        "respond_error": Node(
            type="response",
            params={"include": ["validated"], "status": 422},
            transitions={"success": None},
        ),
    },
)

# 3. Execute
async def main():
    runtime = Runtime(workflow, registry)
    context = await runtime.execute(
        "exec_001",
        input_data={"input": {"name": "Alice", "age": 30, "role": "admin"}},
    )
    print(context.data["response"])
    # {"data": {"validated": {"name": "Alice", "age": 30, "role": "admin"}}, "status": 201}

asyncio.run(main())
```

---

## Core concepts

| Concept | Role |
|---------|------|
| `Workflow` | Defines the state machine — nodes and their transitions |
| `Node` | A state: its type, params, and where it goes next |
| `Runtime` | Drives execution — resolves nodes, runs them, follows transitions |
| `Registry` | Maps node type strings to node classes |
| `Context` | Immutable execution state — carries all data through the flow |
| `Result` | What a node returns on success — output + transition key |
| `NodeError` | What a node returns on failure — code + message + transition key |
| `Event` | Emitted at every execution boundary for observability |

---

## Navigation

- **[Getting Started](getting-started.md)** — installation, first workflow, running it
- **[Concepts](concepts.md)** — state machines, context flow, events
- **[Guides](guides/defining-workflows.md)** — how-to for common tasks
- **[Reference](reference/workflow.md)** — complete API documentation
- **[Examples](examples/user-registration.md)** — end-to-end worked examples
