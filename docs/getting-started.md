# Getting Started

## Installation

```bash
pip install workflow-core
```

With Poetry:

```bash
poetry add workflow-core
```

**Requirements:** Python 3.11+

---

## Your first workflow

This example collects a user's name and age, validates them, and returns a response.

### Step 1 — Create a registry and register node types

```python
from workflow_core import Registry
from workflow_core.nodes import FormNode, ResponseNode

registry = Registry()
registry.register("form")(FormNode)
registry.register("response")(ResponseNode)
```

The registry maps string type names (used in the workflow definition) to the actual node classes that execute them.

### Step 2 — Define the workflow

```python
from workflow_core import Workflow, Node

workflow = Workflow(
    id="collect_user",
    start="collect",
    nodes={
        "collect": Node(
            type="form",
            params={
                "fields": {
                    "name": {"type": "str", "required": True},
                    "age":  {"type": "int",  "required": True, "min": 0, "max": 150},
                }
            },
            transitions={
                "success": "ok",
                "failure": "error",
            },
        ),
        "ok": Node(
            type="response",
            params={"status": 200, "include": ["validated"]},
            transitions={"success": None},
        ),
        "error": Node(
            type="response",
            params={"status": 422},
            transitions={"success": None},
        ),
    },
)
```

`transitions` maps outcome keys to the next node. `None` means the workflow ends.

### Step 3 — Execute

```python
import asyncio
from workflow_core import Runtime

async def main():
    runtime = Runtime(workflow, registry)

    # valid input
    context = await runtime.execute(
        execution_id="exec_001",
        input_data={"input": {"name": "Alice", "age": 30}},
    )
    print(context.data["response"])
    # {"data": {"validated": {"name": "Alice", "age": 30}}, "status": 200}

    # invalid input
    context = await runtime.execute(
        execution_id="exec_002",
        input_data={"input": {"name": "Alice", "age": -5}},
    )
    print(context.data["response"])
    # {"data": {...}, "status": 422}

asyncio.run(main())
```

---

## What just happened

```
input_data arrives
    ↓
"collect" node (FormNode)
    validates name and age
    → success: data is valid → go to "ok"
    → failure: data invalid  → go to "error"
    ↓
"ok" or "error" node (ResponseNode)
    shapes the response
    → success: None → workflow ends
    ↓
context.data["response"] is the result
```

The runtime followed the state machine. Each node ran, returned an outcome, and the runtime followed the transition to the next state.

---

## Next steps

- [Concepts](concepts.md) — understand state machines, context, and events
- [Defining Workflows](guides/defining-workflows.md) — the full workflow API
- [Custom Nodes](guides/custom-nodes.md) — build your own node types
- [Examples](examples/user-registration.md) — complete real-world flows
