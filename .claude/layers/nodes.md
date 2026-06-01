# src/workflow_core/nodes/ — Built-in Node Implementations

Six node types ship with the library. They cover the full surface of a web application:
form → decision → http → transform → persist → response.

No framework imports allowed here. Nodes are pure async executors.

---

## Built-in Node Inventory

| Node | File | Replaces in Django/FastAPI |
|------|------|---------------------------|
| `form` | `form.py` | DRF serializer + view input validation |
| `decision` | `decision.py` | `if/elif` chains in service layer |
| `http` | `http.py` | `requests.post()` / outbound API calls |
| `transform` | `transform.py` | Serializer `to_representation` / data mapping |
| `persist` | `persist.py` | `model.save()` / ORM read-write |
| `response` | `response.py` | `return Response(...)` / response shaping |

---

## form

Validates user-supplied input against a field schema defined in `FormNodeConfig`.

- Fields declare: name, type, required, validators (min, max, regex, enum values)
- On failure: returns `FailedNodeResult` with `code="VALIDATION_FAILED"` and per-field errors
- On success: merges validated fields into `NodeResult.output`
- Never calls an external service — pure validation only

---

## decision

Evaluates a condition expression against `ExecutionContext.data` and selects a transition branch.

- Condition is a simple expression string: `"context.kyc_status == 'approved'"`
- Condition evaluation is deterministic — same context always produces same branch
- Never calls external services or reads config inside condition evaluation
- Returns `NodeResult` with `outcome` set to the matched branch key

---

## http

Executes an outbound HTTP request using `httpx.AsyncClient`.

- Method, URL, headers, and body template are declared in `HTTPNodeConfig`
- Body template supports `{{ context.field }}` interpolation against `ExecutionContext.data`
- Response is stored in `NodeResult.output` under `http_response`
- HTTP 4xx/5xx → `FailedNodeResult` with `code="HTTP_ERROR"` and status code in context
- Never uses `requests` — always `httpx.AsyncClient`

---

## transform

Applies a field mapping to reshape `ExecutionContext.data`.

- Mapping is declarative: `{"target_field": "source.nested.field"}`
- Pure function — no I/O, no async
- Used to rename, project, or flatten context fields before downstream nodes

---

## persist

Reads from or writes to the configured storage backend via the repository interface.

- Operation is one of: `read`, `write`, `update`, `delete`
- Model and key are declared in `PersistNodeConfig`
- Calls `AbstractRepository` — never touches Redis/DB driver directly
- On write: stores entity, returns saved record in `NodeResult.output`
- On read-not-found: returns `FailedNodeResult` with `code="RECORD_NOT_FOUND"`

---

## response

Shapes the final API response from `ExecutionContext.data`.

- Field projection: declares which context fields to include in the response body
- Status code declared in config (default 200)
- Output stored in `NodeResult.output["response"]` — adapter reads this to build HTTP response
- Always the terminal node in a workflow path — transitions to `null`

---

## Adding a New Built-in Node

1. Create `src/workflow_core/nodes/<name>.py` with the node class and its `NodeConfig` subclass
2. Add the `NodeType` enum value to `src/workflow_core/constants.py`
3. Register in `workflow_core/registry.py`
4. Write executor integration tests in `tests/nodes/`
5. Document the node in this file

Never add a built-in node without completing all five steps.
