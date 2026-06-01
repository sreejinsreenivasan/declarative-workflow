# /review

Review the current diff against project conventions and produce a structured findings report.

## What to check

### BLOCKER
- `core/` imports from `nodes/` or `adapters/`
- Node mutates `inputs.context` directly
- Blocking I/O (`requests`, `time.sleep`, sync DB call) in async path
- `WorkflowError` not used — raw exception bubbles to consumer
- Hardcoded credentials, URLs, or DSNs
- Missing `async def` on a method that performs I/O
- `WorkflowDefinition` or `ExecutionContext` mutated in place

### HIGH
- 85% coverage not maintained
- No failing test exists before new logic (TDD violated)
- `dict` crossing a layer boundary instead of a typed entity
- Magic string used instead of enum
- Function, class, or file over size limit with no refactor plan

### MEDIUM
- Missing audit log for a state transition
- `NodeConfig` not validated at construction time
- Test covers only happy path when error paths exist
- `model_copy` pattern not used — direct assignment on frozen model attempted

### LOW
- Naming inconsistency with project conventions
- Comment explains WHAT instead of WHY
- Unnecessary `async def` on a pure transformation with no I/O

## Output format

```markdown
## Findings

### BLOCKER
- <description with file:line>

### HIGH
- <description with file:line>

### MEDIUM
- <description with file:line>

### LOW
- <description with file:line>
```
