# Node Contract Rules

These rules apply to all files in `workflow_core/nodes/` and any user-defined node.

---

## Every Node Must

- Implement `NodeProtocol`: `async def execute(self, inputs: NodeInputs) -> NodeResult`
- Return `NodeResult` on success or `FailedNodeResult` on failure — never raise
- Be stateless — no mutable instance state between executions
- Log execution start and completion with `node_id`
- Declare its `NodeType` enum value as a class attribute

---

## Every Node Must Never

- Call another node directly — runtime drives sequencing
- Write to `inputs.context` directly — return output in `NodeResult.output`
- Import from `workflow_core/adapters/` — nodes are framework-agnostic
- Use `requests`, `time.sleep`, or any sync I/O
- Swallow exceptions silently — always surface as `FailedNodeResult`

---

## NodeConfig

Each node type defines its own `NodeConfig` subclass:

```python
class MyNodeConfig(NodeConfig):
    my_setting: str
    transitions: dict[str, str | None]
```

Config is validated at `WorkflowDefinition` construction.
Invalid config raises `WorkflowError` before execution starts.

---

## Registering a Custom Node

```python
from workflow_core.registry import NodeRegistry

@NodeRegistry.register("my_node")
class MyNode:
    async def execute(self, inputs: NodeInputs) -> NodeResult:
        value = inputs.context.data.get("some_key")
        return NodeResult(output={"result": value}, outcome="success")
```

- Type string must be unique — re-registration raises `NodeTypeConflictError`
- Registration validates `NodeProtocol` compliance at import time

---

## Adding a Built-in Node (checklist)

1. `workflow_core/nodes/<name>.py` — node class + `NodeConfig` subclass
2. `workflow_core/core/constants.py` — add `NodeType` enum value
3. `workflow_core/registry.py` — register the node
4. `tests/nodes/test_<name>_node.py` — unit tests (happy + error paths)
5. `workflow_core/nodes/AGENTS.md` — document the node in the inventory table
