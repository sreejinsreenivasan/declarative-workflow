# Testing Rules

These rules apply to all files in `tests/`.

---

## TDD — Mandatory

Red → Green → Refactor, every time.
A PR without a prior failing test for new logic is sent back.

---

## Coverage

85% minimum per module. Never regress on a PR.

```bash
poetry run pytest --cov=workflow_core --cov-report=term-missing
```

---

## Async Tests

All async tests use `async def`. `asyncio_mode = auto` in `pyproject.toml`.

```python
# correct
async def test_execute_workflow_returns_completed():
    result = await runtime.execute_async("exec_001", {})
    assert result.status == ExecutionStatus.COMPLETED

# wrong — never use asyncio.run() inside a test
def test_execute():
    result = asyncio.run(runtime.execute_async("exec_001", {}))
```

---

## Mocking Rules

- Mock at the boundary — never inside `core/`
- Redis: mock `redis.asyncio` driver via `AsyncMock`
- HTTP: mock `httpx.AsyncClient` — never real network calls in unit/CI tests
- Live-infrastructure tests: `@pytest.mark.integration`, excluded from default run

---

## Naming

```
tests/<layer>/test_<subject>_<condition>_<outcome>.py   (file)
test_<action>_<scenario>                                (function)
```

Examples:
```
test_http_node_with_5xx_response_returns_failed_result
test_form_node_with_missing_required_field_returns_validation_error
test_decision_node_evaluates_to_correct_branch
```

---

## Fixtures

Standard names in `conftest.py`:
- `minimal_workflow` — one-node `WorkflowDefinition`
- `mock_repository` — `AbstractRepository` returning deterministic data
- `async_redis_mock` — mocked `redis.asyncio` client

---

## Anti-Patterns

Reject these in review:
- Snapshot tests replacing real assertions
- Happy-path-only tests when error paths exist
- `time.sleep` in any test
- `assert True` or empty test bodies
- Mocking non-boundary code inside `core/`
