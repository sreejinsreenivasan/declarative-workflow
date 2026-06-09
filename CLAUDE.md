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
src/workflow_core/entities/   ← domain entities; pure (stdlib + Pydantic only)
src/workflow_core/execution/  ← pipeline executor and state manager; pure
src/workflow_core/nodes/      ← node protocol + built-in implementations
src/workflow_core/adapters/   ← FastAPI + Redis; framework imports live here only
tests/                        ← pytest suites mirroring src/ layout
```

Dependency direction is strict and one-way:
`adapters/` → `nodes/` → `entities/` + `execution/`. Inner layers never import from outer.

---

## Key Files

| Path | Role |
|------|------|
| `src/workflow_core/runtime.py` | `WorkflowRuntime` — main public entry point |
| `src/workflow_core/registry.py` | `NodeRegistry` — maps type strings to node classes |
| `src/workflow_core/execution/executor.py` | `PipelineExecutor` — sync + async pipeline runner |
| `src/workflow_core/execution/state_manager.py` | Pure state transition functions |
| `src/workflow_core/entities/workflow.py` | `WorkflowDefinition` — top-level domain object |
| `src/workflow_core/entities/context.py` | `ExecutionContext` — immutable execution state carrier |
| `src/workflow_core/entities/result.py` | `NodeResult`, `FailedNodeResult` — typed outputs |
| `src/workflow_core/nodes/protocol.py` | `NodeProtocol` — contract every node must satisfy |
| `src/workflow_core/nodes/` | Built-in nodes: form, decision, http, transform, persist, response |
| `src/workflow_core/adapters/fastapi.py` | `workflow_router()` — mounts workflow to FastAPI app |
| `src/workflow_core/adapters/redis.py` | Redis execution state repository |

---

## Approval Gate

Present a plan and wait for explicit approval before modifying:
- `src/workflow_core/execution/`
- `src/workflow_core/entities/`
- `src/workflow_core/runtime.py`
- `src/workflow_core/nodes/protocol.py`

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
