# Runtime

```python
from workflow_core import Runtime
```

Drives workflow execution. Resolves nodes, runs them, follows transitions, emits events, and returns the final context.

---

## Constructor

```python
Runtime(workflow: Workflow, registry: Registry)
```

| Param | Type | Description |
|-------|------|-------------|
| `workflow` | `Workflow` | The state machine definition |
| `registry` | `Registry` | Maps node type strings to node classes |

---

## execute()

```python
async def execute(
    execution_id: str,
    input_data: dict[str, Any] | None = None,
    on_event: Callable | None = None,
) -> Context
```

Runs the workflow from `start` to completion.

| Param | Type | Description |
|-------|------|-------------|
| `execution_id` | `str` | Unique identifier for this execution run |
| `input_data` | `dict \| None` | Initial data placed in `context.data` |
| `on_event` | `Callable \| None` | Called with each `Event`. Supports sync and async |

Returns the final `Context` after the loop exits (`context.node is None`).

---

## Execution loop

```
Create Context(node=workflow.start, data=input_data)
↓
while context.node is not None:
    emit NODE_STARTED
    resolve and instantiate node from registry
    result = await node.run(context, params)
    emit NODE_COMPLETED
    validate transition exists
    emit TRANSITION_SELECTED
    context = merge output + advance node
↓
emit WORKFLOW_COMPLETED
return context
```

### Exception handling

If a node raises an unhandled exception, the runtime catches it and produces:

```python
NodeError(code="UNEXPECTED_ERROR", message=str(exc))
```

The `"failure"` transition is then followed. If no `"failure"` transition exists on the node, the runtime raises `RuntimeError`.

### Unknown transitions

If a node returns a transition key not declared in the node's `transitions` dict, the runtime raises immediately:

```python
RuntimeError: node 'verify_kyc': unknown transition 'approved'
```

---

## Example

```python
from workflow_core import Runtime, Registry, Workflow, Node
from workflow_core.nodes import FormNode, ResponseNode

registry = Registry()
registry.register("form")(FormNode)
registry.register("response")(ResponseNode)

workflow = Workflow(
    id="w",
    start="collect",
    nodes={
        "collect": Node(
            type="form",
            params={"fields": {"name": {"type": "str"}}},
            transitions={"success": "done", "failure": "done"},
        ),
        "done": Node(type="response", transitions={"success": None}),
    },
)

runtime = Runtime(workflow, registry)

context = await runtime.execute(
    execution_id="exec_001",
    input_data={"input": {"name": "Alice"}},
    on_event=print,
)

print(context.data["response"])
```
