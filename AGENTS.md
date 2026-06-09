# workflow-core — Agent Guide

Installable Python library for declarative, pipeline-based workflow execution.
Workflows are defined in Python using Pydantic schemas, executed by a generic async runtime,
and mounted to web frameworks via thin adapters.

---

## Architecture

```
src/workflow_core/entities/   → domain entities; pure (stdlib + Pydantic only)
src/workflow_core/execution/  → pipeline executor and state manager; pure
src/workflow_core/nodes/      → node protocol + built-in implementations
src/workflow_core/adapters/   → FastAPI + Redis; only place framework imports appear
tests/                        → pytest suites mirroring src/ layout
```

Dependency direction is strict and one-way: `adapters/` → `nodes/` → `entities/` + `execution/`.
Inner layers never import from outer layers.

Detailed rules per layer:

- Pure domain logic → `.claude/layers/core.md`
- Execution engine → `.claude/layers/core-execution.md`
- Domain entities → `.claude/layers/core-entities.md`
- Node protocol → `.claude/layers/core-nodes.md`
- Built-in nodes → `.claude/layers/nodes.md`
- Adapters → `.claude/layers/adapters.md`
- Testing conventions → `.claude/layers/tests.md`

---

## Mandatory Engineering Principles

### 1. Functional-First

Prefer pure functions over stateful classes. Side-effect-free transformations
are easier to test, trace, and compose.

**Prefer:**
```python
def resolve_next_node(transitions: dict[str, str | None], outcome: str) -> str | None:
    return transitions.get(outcome)
```

**Avoid:**
```python
class TransitionResolver:
    def __init__(self):
        self._last = None
    def resolve(self, transitions, outcome):
        self._last = transitions.get(outcome)
        return self._last
```

Use classes only for: domain entities, repository interfaces, async infrastructure adapters,
and DI boundaries.

---

### 2. Async-First

All I/O must be async. No `requests`, no `time.sleep`, no synchronous DB calls in
async paths. Use `httpx.AsyncClient`, `redis.asyncio`.

Processors and node `execute()` methods that perform I/O must be `async def`.
Pure transformation helpers that do no I/O must be plain `def`.

---

### 3. TDD

Red → Green → Refactor, every time.
Tests live next to the code they cover (`tests/core/`, `tests/nodes/`, `tests/adapters/`).
A PR with new logic and no prior failing test does not follow TDD — send it back.

---

### 4. Pydantic v2 for All Schemas

- Public API schemas, node configs, and domain entities use `BaseModel`
- Internal execution state (no public surface) uses `dataclass`
- No raw `dict` flows across layer boundaries
- Public functions never return `dict[str, Any]` — always return a typed `BaseModel`
- `Any` is a last resort; every use requires an inline comment explaining why no concrete type exists

---

### 5. Immutability

Domain entities are Pydantic `BaseModel` instances with `model_config = ConfigDict(frozen=True)`.
Use `model.model_copy(update={...})` to derive modified instances — never mutate in place.

`ExecutionContext` is append-only. Nodes add to `context.data`; they never delete or
overwrite keys set by earlier nodes.

---

### 6. Prefer the Typed Ecosystem

Every value that belongs to a fixed set must use an enum or a typed model — not a plain `str`, `int`, or `dict`.

This applies to:
- Node types, execution statuses, transition outcomes, error codes
- UI component types, style variants, button sizes, input types
- Any parameter or field whose valid values can be enumerated

```python
# correct — enum for a fixed set of variants
class ButtonVariant(str, Enum):
    PRIMARY = "primary"
    DESTRUCTIVE = "destructive"
    GHOST = "ghost"

def button(text: str, *, variant: ButtonVariant = ButtonVariant.PRIMARY) -> ButtonComponent: ...

# wrong — open string leaks the constraint into caller code
def button(text: str, *, variant: str = "primary") -> dict[str, Any]: ...
```

Collections that key or branch on a type value must use the enum as the key — never a bare string literal:

```python
# correct
_FIELD_TYPES: frozenset[ComponentType] = frozenset({ComponentType.INPUT, ComponentType.SELECT})

# wrong
_FIELD_TYPES = {"input", "select"}
```

Use `str`-based enums (`class Foo(str, Enum)`) so values remain JSON-serialisable without extra conversion.

---

### 7. No Hardcoded Config or Secrets

Use pydantic-settings (`workflow_core/config.py`) and environment variables.
Never commit credentials, DSNs, or URLs.

---

### 8. Structured Errors

All errors raised by the library carry:

```python
WorkflowError(
    code="NODE_EXECUTION_FAILED",
    message="HTTP node 'verify_kyc' returned status 422.",
    context={"node_id": "verify_kyc", "status_code": 422},
)
```

Never let raw Python exceptions bubble to library consumers.

---

### 9. Audit-Safe by Default

Every state transition logs `execution_id`, `node_id`, `status`, and `timestamp`.
PII must never appear in log messages.

---

## Size Limits

| Unit | Limit |
|------|-------|
| Function | < 30 lines |
| Class | < 300 lines |
| File | < 400 lines |

Flag violations in review. Refactor before adding more logic.

---

## Node Contract (summary)

Every node — built-in or user-defined — must satisfy `NodeProtocol`:

```python
class MyNode:
    async def execute(self, inputs: NodeInputs) -> NodeResult:
        ...
```

A node must:
- Be a pure async executor with no global or shared mutable state
- Return a typed `NodeResult` (or `FailedNodeResult`)
- Never call another node directly — the runtime drives sequencing
- Never mutate `ExecutionContext` directly — return output data in `NodeResult`

Full contract in `workflow_core/core/nodes/AGENTS.md`.

---

## Execution Invariants

1. **A node executes only once per path** — executor checks node status before execution
2. **Context is append-only** — nodes add to `context.data`, never overwrite prior keys
3. **WorkflowDefinition is never mutated during execution** — all state lives in `ExecutionContext`
4. **State is persisted before and after each node** — repository called at both checkpoints

---

## Review Checklist

Before marking a PR ready:

- [ ] Failing test exists before the fix (TDD)
- [ ] 85% module coverage maintained
- [ ] No business logic in adapters or routes
- [ ] No blocking I/O in async paths
- [ ] Audit logging present for state transitions
- [ ] No hardcoded secrets, URLs, or magic strings
- [ ] No `-> dict[str, Any]` on public functions — typed `BaseModel` returned instead
- [ ] No plain `str` parameter where an enum covers a fixed set of values
- [ ] No `Any` without an inline comment explaining why no concrete type fits
- [ ] Structured `WorkflowError` with `code`, `message`, `context`
- [ ] `ruff`, `black`, `isort`, `mypy` pass clean
- [ ] `core/` imports nothing from `nodes/` or `adapters/`

---

## Review Output Format

```markdown
## Findings

### BLOCKER
- <must fix before merge>

### HIGH
- <significant architectural or security risk>

### MEDIUM
- <maintainability concern>

### LOW
- <improvement suggestion>
```

---

## Default Principle

When uncertain: **TDD + Async-first + Immutable context + Audit-safe**.
Correctness and safety always outweigh speed or cleverness.
