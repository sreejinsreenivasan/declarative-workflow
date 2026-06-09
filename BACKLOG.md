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
