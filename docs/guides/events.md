# Events & Observability

The runtime emits an `Event` at every execution boundary. Events are immutable, timestamped, and carry structured data. They are the observability surface of the library.

---

## Event types

| Type | When emitted |
|------|-------------|
| `node.started` | Before `node.run()` is called |
| `node.completed` | After `node.run()` returns, carries `transition` key |
| `transition.selected` | After next node resolved, carries `transition` and `next` |
| `context.updated` | Reserved for future use |
| `workflow.completed` | After the execution loop exits |
| `workflow.failed` | If the runtime raises |

---

## Subscribing to events

Pass an `on_event` callback to `runtime.execute()`:

```python
from workflow_core import Event

events: list[Event] = []

context = await runtime.execute(
    "exec_001",
    input_data={...},
    on_event=events.append,
)
```

Async callbacks are also supported:

```python
async def handle_event(event: Event) -> None:
    await log_to_db(event)

context = await runtime.execute("exec_001", on_event=handle_event)
```

---

## Event structure

```python
Event(
    type=EventType.NODE_COMPLETED,
    execution_id="exec_001",
    node_id="verify_kyc",
    timestamp=datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
    data={"transition": "success"},
)
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | `EventType` | The event category |
| `execution_id` | `str` | Identifies the execution run |
| `node_id` | `str \| None` | The node that emitted the event |
| `timestamp` | `datetime` | UTC timestamp, set automatically |
| `data` | `dict` | Event-specific payload |

---

## Common patterns

### Logging

```python
import logging

logger = logging.getLogger("workflow")

def log_event(event: Event) -> None:
    logger.info(
        "%s node=%s execution=%s",
        event.type.value,
        event.node_id,
        event.execution_id,
        extra=event.data,
    )

context = await runtime.execute("exec_001", on_event=log_event)
```

### Measuring execution time

```python
from datetime import datetime, timezone

start_times: dict[str, datetime] = {}

def track_timing(event: Event) -> None:
    if event.type == EventType.NODE_STARTED and event.node_id:
        start_times[event.node_id] = event.timestamp

    if event.type == EventType.NODE_COMPLETED and event.node_id:
        started = start_times.get(event.node_id)
        if started:
            duration_ms = (event.timestamp - started).total_seconds() * 1000
            print(f"{event.node_id} took {duration_ms:.1f}ms")
```

### Audit trail

```python
audit_log: list[dict] = []

def audit(event: Event) -> None:
    if event.type in (EventType.NODE_COMPLETED, EventType.WORKFLOW_COMPLETED):
        audit_log.append({
            "execution_id": event.execution_id,
            "event":        event.type.value,
            "node":         event.node_id,
            "timestamp":    event.timestamp.isoformat(),
            "data":         event.data,
        })
```

### SSE streaming (FastAPI)

```python
from fastapi.responses import StreamingResponse
import json

async def execute_and_stream(execution_id: str, input_data: dict):
    async def event_stream():
        async def push(event: Event) -> None:
            payload = json.dumps({
                "type": event.type.value,
                "node": event.node_id,
                "data": event.data,
            })
            yield f"data: {payload}\n\n"

        context = await runtime.execute(execution_id, input_data, on_event=push)
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

---

## Replayability

Because events are immutable and timestamped, you can store them and replay execution history:

```python
# store all events
stored_events: list[dict] = []

async def persist_event(event: Event) -> None:
    stored_events.append(event.model_dump())

await runtime.execute("exec_001", input_data={...}, on_event=persist_event)

# later: reconstruct what happened
for event in stored_events:
    print(f"[{event['timestamp']}] {event['type']} @ {event['node_id']}")
```
