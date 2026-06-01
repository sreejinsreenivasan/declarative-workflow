# Event

```python
from workflow_core import Event, EventType
```

Emitted by the runtime at every execution boundary. Immutable and timestamped.

---

## Event fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | `EventType` | Event category |
| `execution_id` | `str` | Identifies the execution run |
| `node_id` | `str \| None` | The node that emitted the event. `None` for workflow-level events |
| `timestamp` | `datetime` | UTC timestamp, set automatically |
| `data` | `dict[str, Any]` | Event payload |

---

## EventType

| Value | Constant | `data` keys |
|-------|----------|-------------|
| `"node.started"` | `EventType.NODE_STARTED` | — |
| `"node.completed"` | `EventType.NODE_COMPLETED` | `transition` |
| `"transition.selected"` | `EventType.TRANSITION_SELECTED` | `transition`, `next` |
| `"context.updated"` | `EventType.CONTEXT_UPDATED` | reserved |
| `"workflow.completed"` | `EventType.WORKFLOW_COMPLETED` | — |
| `"workflow.failed"` | `EventType.WORKFLOW_FAILED` | — |

---

## Subscribing

Pass `on_event` to `runtime.execute()`. Both sync and async callbacks are supported:

```python
# sync
context = await runtime.execute("e1", on_event=print)

# async
async def on_event(event: Event) -> None:
    await save_to_audit_log(event)

context = await runtime.execute("e1", on_event=on_event)
```

See [Events & Observability](../guides/events.md) for patterns.
