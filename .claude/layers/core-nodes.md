# core/nodes/ — Node Protocol & Boundaries

Defines the contract every node — built-in or user-defined — must satisfy.
This is the public extension boundary of the library.

---

## NodeProtocol

Every node must implement `NodeProtocol` (structural typing via `typing.Protocol`):

```python
class NodeProtocol(Protocol):
    async def execute(self, inputs: NodeInputs) -> NodeResult:
        ...
```

A node that does not satisfy this protocol will be rejected at registration time.

---

## NodeInputs

`NodeInputs` carries everything a node needs to execute:

| Field | Type | Description |
|-------|------|-------------|
| `node_id` | `str` | The node's ID within the workflow |
| `config` | `NodeConfig` | Static configuration from `WorkflowDefinition` |
| `context` | `ExecutionContext` | Read-only snapshot of current execution state |

A node reads from `inputs.context.data` but **never writes to it directly**.
Output data is returned inside `NodeResult.output`.

---

## NodeResult

```python
class NodeResult(BaseModel):
    output: dict[str, Any]        # data merged into context by the runtime
    outcome: str                  # transition key: "success", "failure", etc.

class FailedNodeResult(BaseModel):
    error: WorkflowError          # structured error — never a raw exception
```

A node always returns one of these two types. Never raises an unhandled exception.

---

## What a Node Must Do

- Be `async def execute(...)` — no sync node implementations
- Return a typed `NodeResult` or `FailedNodeResult`
- Log execution start and completion using the library logger
- Declare its expected `NodeType` as a class attribute for registry validation

---

## What a Node Must Never Do

- Call another node directly — the runtime drives sequencing
- Mutate `inputs.context` or any shared object
- Import from `src/workflow_core/adapters/` — nodes are framework-agnostic
- Swallow exceptions silently — always return `FailedNodeResult` on error
- Hold mutable instance state between executions — nodes are stateless

---

## Custom Node Registration

User-defined nodes are registered via `NodeRegistry`:

```python
from workflow_core.registry import NodeRegistry

@NodeRegistry.register("send_email")
class SendEmailNode:
    async def execute(self, inputs: NodeInputs) -> NodeResult:
        ...
```

Registration validates that the class satisfies `NodeProtocol`.
A node type string must be unique — re-registering an existing type raises `NodeTypeConflictError`.

---

## NodeConfig

`NodeConfig` is a Pydantic `BaseModel` defined per node type.
Each built-in node defines its own config subclass in `src/workflow_core/nodes/`.
User-defined nodes must define their own `NodeConfig` subclass.

```python
class HTTPNodeConfig(NodeConfig):
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    transitions: dict[str, str | None]
```

Config is validated at `WorkflowDefinition` construction — invalid config raises before execution starts.
