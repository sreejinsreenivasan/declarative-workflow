# src/workflow_core/adapters/ — Framework & Storage Adapters

Adapters are the only place in the library where framework imports (FastAPI, redis) appear.
They translate between the library's domain types and the outside world.

---

## Adapter Contract

An adapter:
- Accepts HTTP requests or domain entities as input
- Returns domain entities or HTTP responses as output
- Has no knowledge of business rules or node logic
- Is always async

---

## fastapi.py — FastAPI Adapter

Exposes `workflow_router(workflow: WorkflowDefinition) -> APIRouter`.

Responsibilities:
- Mount a POST endpoint at `/{workflow_id}/execute`
- Extract `input_data` from the request body (Pydantic-parsed)
- Call `WorkflowRuntime.execute_async(execution_id, input_data)`
- Read `context.data["response"]` and return as `JSONResponse`
- Map `WorkflowError` to structured HTTP error responses via a central exception handler

Rules:
- Route handler calls exactly one runtime method — no business logic inline
- Auth is enforced via FastAPI `Depends` — never inline in the route handler
- Never log request body contents — may contain PII
- All errors use the structured format: `{"code": "...", "message": "...", "context": {...}}`

---

## redis.py — Redis Persistence Adapter

Implements `AbstractRepository[ExecutionContext]` against `redis.asyncio`.

Rules:
- All Redis calls use `await` — never synchronous `redis-py`
- TTL is always explicit on every write — never cache without expiry
- Key format: `workflow:{workflow_id}:execution:{execution_id}`
- Serialize with `context.model_dump_json()`, deserialize with `ExecutionContext.model_validate_json()`
- Connection pool is initialized once at startup — never create a new client per request
- Read-not-found returns `None`, never raises `KeyError`

---

## AbstractRepository

`abstract_repository.py` defines the interface the `persist` node calls.
Redis is the default implementation. To add a new backend:

1. Create a new adapter file (e.g. `postgres.py`)
2. Implement `AbstractRepository`
3. Wire it via the DI factory in `workflow_core/dependencies.py`
4. No changes to `persist` node or core execution logic

---

## Tests

Adapter tests live in `tests/adapters/`. Tests mock the Redis driver and
`httpx` client at the boundary — never make real network calls in unit or CI tests.

Mark tests requiring live infrastructure with `@pytest.mark.integration`
and exclude from the default pytest run via `pytest.ci.ini`.
