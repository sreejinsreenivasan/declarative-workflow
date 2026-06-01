# Code Style Rules

These rules apply to all Python files in this project.

---

## Functional-First

Prefer pure functions over stateful classes.

```python
# prefer
def resolve_transition(transitions: dict[str, str | None], outcome: str) -> str | None:
    return transitions.get(outcome)

# avoid
class TransitionResolver:
    def resolve(self, transitions, outcome): ...
```

Use classes only for: domain entities, repository interfaces, async adapters, DI boundaries.

---

## Async-First

All I/O must be async. No exceptions.

| Forbidden | Use instead |
|-----------|-------------|
| `requests` | `httpx.AsyncClient` |
| `time.sleep` | `asyncio.sleep` |
| `redis-py` sync | `redis.asyncio` |
| `asyncio.run()` inside async code | structural issue — investigate |

Pure transformation helpers (no I/O) must be plain `def`, not `async def`.

---

## Pydantic v2

- Public schemas, API models, domain entities → `BaseModel`
- Internal execution state (no public surface) → `dataclass`
- No raw `dict` crosses a layer boundary
- Use `model_copy(update={...})` — never `model.field = value` on frozen models
- Validators live inside the entity — not re-implemented in services

---

## Enums Over Magic Strings

```python
# correct
if status == NodeStatus.COMPLETED:

# wrong
if status == "completed":
```

All enums live in `workflow_core/core/constants.py` or alongside the model they describe.

---

## Immutability

All domain entities use `model_config = ConfigDict(frozen=True)`.
Produce modified instances with `model_copy(update={...})`.

---

## Size Limits

| Unit | Limit |
|------|-------|
| Function | < 30 lines |
| Class | < 300 lines |
| File | < 400 lines |

Flag in review. Refactor before adding more logic to an over-limit file.

---

## No Hardcoded Config

- Settings → `workflow_core/config.py` (pydantic-settings, env-driven)
- No URLs, DSNs, credentials, or magic constants inline
- Feature variation → settings flag, never `if ENV == "prod"`

---

## Error Handling

All errors raised by the library use `WorkflowError`:

```python
raise WorkflowError(
    code="NODE_EXECUTION_FAILED",
    message="HTTP node 'verify_kyc' returned status 422.",
    context={"node_id": "verify_kyc", "status_code": 422},
)
```

Never let raw Python exceptions bubble to library consumers.
