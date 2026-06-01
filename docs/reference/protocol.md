# NodeProtocol

```python
from workflow_core import NodeProtocol
```

The interface every node must satisfy. Uses structural typing (`typing.Protocol`) — no inheritance required.

---

## Protocol definition

```python
class NodeProtocol(Protocol):
    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        ...
```

Any class with this method signature satisfies the protocol.

---

## Parameters

| Param | Type | Description |
|-------|------|-------------|
| `context` | `Context` | Current immutable execution state. Read from `context.data`. Never write to it. |
| `params` | `dict[str, Any]` | Static configuration from `Node.params` in the workflow definition |

## Returns

| Type | When |
|------|------|
| `Result` | Node completed successfully |
| `NodeError` | Node encountered a handled failure |

Never raise exceptions — always return `NodeError`.

---

## Minimal implementation

```python
from workflow_core import Context
from workflow_core.result import Result, NodeError


class MyNode:
    async def run(self, context: Context, params: dict) -> Result | NodeError:
        value = context.data.get("some_key")

        if not value:
            return NodeError(code="MISSING_VALUE", message="some_key not in context")

        return Result(output={"processed": value})
```

See [Custom Nodes](../guides/custom-nodes.md) for full guidance.
