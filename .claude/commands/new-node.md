# /new-node

Scaffold a new built-in node type following all project conventions.

## Usage

```
/new-node <node_type_name>
```

Example: `/new-node email`

## Steps

1. Create `src/workflow_core/nodes/<name>.py`:
   - Define `<Name>NodeConfig(NodeConfig)` with all required config fields and `transitions`
   - Define `<Name>Node` implementing `NodeProtocol`
   - `async def execute(self, inputs: NodeInputs) -> NodeResult | FailedNodeResult`
   - Add logging at execution start and completion
   - Handle all failure cases with `FailedNodeResult`

2. Add `<NAME> = "<name>"` to `NodeType` enum in `src/workflow_core/constants.py`

3. Register in `src/workflow_core/registry.py`:
   ```python
   from workflow_core.nodes.<name> import <Name>Node
   NodeRegistry.register(NodeType.<NAME>, <Name>Node)
   ```

4. Write tests in `tests/nodes/test_<name>_node.py`:
   - Happy path test
   - Each failure mode test
   - Config validation test (invalid config raises at construction)

5. Add the node to the inventory table in `.claude/layers/nodes.md`

## Rules

- Node file must be < 400 lines
- `execute()` must be < 30 lines — extract helpers if needed
- No framework imports (`fastapi`, `redis`) in the node file
- No direct mutation of `inputs.context`
- All error paths return `FailedNodeResult` — never raise unhandled exceptions
