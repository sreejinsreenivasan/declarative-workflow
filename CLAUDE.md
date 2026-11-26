# workflow-core

Declarative, pipeline-based workflow runtime library for Python web servers.
`pip install workflow-core` — define workflows in Python with Pydantic, mount to FastAPI or Django.

See [AGENTS.md](./AGENTS.md) for full engineering principles, architecture rules, and review checklist.
See [.claude/layers/](./claude/layers/) for per-layer rules (entities, execution, nodes, adapters, tests).

---

## Stack

| Tool | Purpose |
|------|---------|
| Python 3.11+ | Language floor |
| Pydantic v2 | All schemas, domain models, validation |
| httpx | Async outbound HTTP |
| redis.asyncio | Default persistence backend |
| FastAPI | Framework adapter (optional extra) |
| Poetry | Package and dependency management |
| pytest + pytest-asyncio | Test runner |
| ruff + black + isort + mypy | Lint, format, type check |

---

## Commands

```bash
# Install
poetry install
poetry install --extras fastapi

# Tests
poetry run pytest
poetry run pytest tests/
poetry run pytest --cov --cov-report=term-missing --maxfail=1

# Quality
ruff check .
black .
isort .
mypy src/

# Build / publish
poetry build
poetry publish --dry-run
```

---

## Architecture

```
src/workflow_core/
  workflow.py  context.py  result.py  event.py   ← domain models; pure (stdlib + Pydantic only)
  runtime.py   registry.py  store.py  protocol.py ← execution engine and contracts; pure
  processors.py                                   ← reusable async processors
  nodes/                                          ← built-in nodes (form, decision, http, ...)
  ui/                                             ← UI component schema + template loader
  adapters/                                       ← FastAPI, Redis, OpenTelemetry, FileStore;
                                                    framework and I/O imports live here only
tests/                                            ← pytest suites (root = runtime/integration)
```

Dependency direction is strict and one-way:
`adapters/` → `nodes/` → core modules. Core modules never import from `nodes/` or `adapters/`.

---

## Key Files

| Path | Role |
|------|------|
| `src/workflow_core/runtime.py` | `Runtime` — executes, suspends, resumes; sets `Context.status` |
| `src/workflow_core/workflow.py` | `Workflow`, `Node` — declarative definition, validated transitions |
| `src/workflow_core/context.py` | `Context`, `ExecutionStatus` — immutable execution state |
| `src/workflow_core/result.py` | `Result`, `NodeError` — typed node outputs |
| `src/workflow_core/registry.py` | `Registry` — maps type strings to node classes or factories |
| `src/workflow_core/protocol.py` | `NodeProtocol` — contract every node must satisfy |
| `src/workflow_core/store.py` | `ExecutionStore` protocol + `InMemoryStore` |
| `src/workflow_core/event.py` | `Event`, `EventType` — lifecycle events |
| `src/workflow_core/nodes/` | Built-in nodes: form, decision, http, transform, persist, response, ui |
| `src/workflow_core/adapters/fastapi.py` | `api_router()`, `ui_router()` — mount a runtime to FastAPI |
| `src/workflow_core/adapters/redis_store.py` | Redis execution store |
| `src/workflow_core/adapters/file_store.py` | `FileStore` — one JSON file per execution |

---

## Approval Gate

Present a plan and wait for explicit approval before modifying:
- `src/workflow_core/runtime.py`
- `src/workflow_core/context.py`, `workflow.py`, `result.py`, `event.py`, `store.py`
- `src/workflow_core/protocol.py`

---

## Commits

Format: `<type>: <subject>`
Types: `feat` | `fix` | `refactor` | `docs` | `test` | `chore`
Subject: lowercase, imperative mood, ≤72 chars, no trailing period.

```
feat: add redis persistence adapter
fix: handle missing transition key in decision node
chore: release 0.2.0
```

Never commit directly to `main`. Always run `poetry run pytest` before committing.

---

## Release Process

1. All tests pass: `poetry run pytest`
2. Bump version: `poetry version <patch|minor|major>`
3. Commit: `git commit -m "chore: release X.Y.Z"`
4. Tag: `git tag -a vX.Y.Z -m "vX.Y.Z"`
5. Push: `git push origin main --tags`
6. Build + publish: `poetry build && poetry publish`

Never tag without a passing test suite. Never publish without a tag.
