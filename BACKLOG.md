# Backlog

Prioritized list of future work.

---

## High Priority

### More Nodes
- [ ] `wait` — pause execution until a condition or timeout
- [ ] `parallel` — fan-out to multiple branches and join results
- [ ] `queue` — enqueue work and resume on completion signal
- [ ] `file_upload` — handle multipart file input within a workflow
- [ ] `webhook` — emit an outbound webhook call as a workflow step

### Observability
- [ ] OpenTelemetry integration — traces and spans per execution
- [ ] Execution tracing — per-node timing, input/output capture, replay support

### Redis Integration
- [ ] Production-grade `RedisRepository` — TTL management, key namespacing, error recovery
- [ ] Execution history queries — list runs by workflow ID, filter by status

---

## Medium Priority

### Documentation
- [ ] More end-to-end examples (approval flow, multi-step onboarding, async job polling)
- [ ] Architectural guide — layer boundaries, DI pattern, custom node authoring
- [ ] Node reference page — one entry per built-in node with config schema and example

---

## Found by dogfooding (Life OS, 2026-11-26)

- [x] Execution status on `Context` (`running/suspended/completed/failed`) — 0.2
- [x] Persist finished executions, not only suspended ones — 0.2
- [x] Emit `WORKFLOW_FAILED`; an error with no route ends the run as FAILED instead of crashing — 0.2
- [x] Keep exception type and traceback in `NodeError.details` — 0.2
- [x] `FileStore` adapter — 0.2
- [ ] Node dependency injection: `Registry` calls `node_cls()` with no arguments; settings arrive via closures/factories. Consider `register(name, factory)` or passing params at construction.
- [ ] Core requires `httpx` and `jinja2` even when no HTTP/UI node is used; make them extras.
- [ ] Publish to PyPI (consumers currently pin a git commit).
- [ ] Sync convenience wrapper for CLI callers (`asyncio.run` boilerplate).
- [ ] `.claude/layers/*.md` still describe the old `entities/` + `execution/` layout and old class names.
- [ ] 2 pre-existing mypy errors in `runtime.py` (`no-any-return` on `node_cls().run`, unused ignore in `_emit`).
