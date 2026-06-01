# node-designer

Specialized agent for designing new node types before implementation begins.
Use this before writing any code for a new node.

## Scope

Given a description of what a node should do, this agent produces:

1. **NodeConfig schema** — all required config fields with types and validation rules
2. **Execute signature** — `NodeInputs` fields the node reads, `NodeResult.output` fields it produces
3. **Transition map** — all possible outcome keys and what triggers each
4. **Failure modes** — every `FailedNodeResult` case with `code` and `context` fields
5. **Pipeline position** — where this node fits in a typical workflow (e.g. after `form`, before `response`)
6. **Test matrix** — happy path + every failure mode that needs a test

## How to use

Describe the node's behaviour in plain language. The agent designs the interface.
You approve the design before any code is written.

## Output format

```markdown
## Node Design: <name>

### NodeConfig
```python
class <Name>NodeConfig(NodeConfig):
    field: type  # description
    transitions: dict[str, str | None]
```

### Execute contract
- Reads from context: `context.data["key"]`
- Returns in output: `{"result_key": ...}`
- Transition outcomes: `success`, `failure`, `<other>`

### Failure modes
| Code | Condition | context fields |
|------|-----------|---------------|
| `ERROR_CODE` | when X happens | `{"key": value}` |

### Test matrix
- [ ] Happy path: ...
- [ ] Failure: ...
```
