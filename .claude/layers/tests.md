# tests/ — Testing Conventions

Tests are co-located with the code they cover. This directory holds
cross-cutting integration tests that span multiple layers.

---

## TDD Workflow

1. **Red** — write the failing test that describes the desired behaviour
2. **Green** — write the minimum code to make it pass
3. **Refactor** — clean up without breaking the test

A PR that introduces new logic without a prior failing test does not follow TDD. Send it back.

---

## Coverage Requirement

Minimum **85% line coverage** per module.

```bash
poetry run pytest --cov=workflow_core --cov-report=term-missing
```

Coverage must not regress on a PR. A new feature that drops a module below 85% blocks merge.

---

## Test Organisation

| Location | What lives there |
|----------|-----------------|
| `tests/core/execution/` | Executor integration tests — full pipeline runs |
| `tests/core/entities/` | Entity validation and invariant tests |
| `tests/core/nodes/` | NodeProtocol contract tests |
| `tests/nodes/` | Built-in node unit tests |
| `tests/adapters/` | FastAPI route tests (`TestClient`) + Redis adapter tests |
| `tests/` (root) | Cross-cutting integration tests |

---

## pytest Configuration

```ini
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

Use `-m "not integration"` for CI runs that exclude live-infrastructure tests.

---

## Async Tests

All async test functions use `async def`. Never use `asyncio.run()` inside a test.

```python
async def test_execute_workflow_returns_completed_context():
    result = await runtime.execute_async("exec_001", input_data={})
    assert result.status == ExecutionStatus.COMPLETED
```

---

## Fixtures and Factories

Reusable fixtures live in `conftest.py` at the nearest common ancestor.

Standard fixture names:
- `minimal_workflow` — a valid `WorkflowDefinition` with a single node
- `completed_context` — an `ExecutionContext` in `COMPLETED` state
- `mock_repository` — a mock `AbstractRepository` returning predictable data
- `async_redis_mock` — a mocked `redis.asyncio` client

---

## Mocking Rules

- Mock at the boundary, not inside `core/`
- Core execution tests run against the real implementation — no mocks
- Redis calls: mock `redis.asyncio` driver methods via `unittest.mock.AsyncMock`
- External HTTP calls: mock `httpx.AsyncClient` — never make real network calls in unit tests
- Mark tests requiring live infrastructure: `@pytest.mark.integration`

---

## Naming Convention

```
tests/<layer>/test_<what>_<condition>_<expected>.py    (file)
test_<action>_<scenario>                               (function)
```

Examples:
- `test_execute_workflow_with_failed_http_node_returns_failed_status`
- `test_form_node_with_missing_required_field_returns_validation_error`
- `test_decision_node_routes_to_correct_branch`

---

## Anti-Patterns to Reject

- Snapshot tests replacing real assertions
- Tests covering only the happy path when error paths exist
- Tests coupled to internal method call counts on non-boundary code
- `time.sleep` in tests
- `assert True` or empty test bodies
- Mocking inside `core/` tests
