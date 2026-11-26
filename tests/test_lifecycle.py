"""Execution lifecycle: status, persistence of finished runs, failure handling.

Found while running Life OS workflow packs on workflow_core (2026-11-26).
"""

import pytest

from workflow_core import ExecutionStatus, InMemoryStore, Runtime
from workflow_core.context import Context
from workflow_core.event import Event, EventType
from workflow_core.registry import Registry
from workflow_core.result import NodeError, Result
from workflow_core.workflow import Node, Workflow

# --- helpers ---


def make_registry(*pairs: tuple[str, type]) -> Registry:
    r = Registry()
    for name, cls in pairs:
        r.register(name)(cls)
    return r


def static_node(result: Result | NodeError) -> type:
    class _Node:
        async def run(self, context: Context, params: dict) -> Result | NodeError:
            return result

    return _Node


def raising_node(exc: Exception) -> type:
    class _Node:
        async def run(self, context: Context, params: dict) -> Result:
            raise exc

    return _Node


def gate_node() -> type:
    """Suspends until context.data['decision'] is set."""

    class _Node:
        async def run(self, context: Context, params: dict) -> Result:
            if context.data.get("decision"):
                return Result(transition="approved")
            return Result(transition="waiting")

    return _Node


def single(node_type: str, transitions: dict[str, str | None]) -> Workflow:
    return Workflow(id="w", start="a", nodes={"a": Node(type=node_type, transitions=transitions)})


def recorder() -> tuple[list[Event], object]:
    events: list[Event] = []
    return events, events.append


# --- A. status ---


def test_new_context_defaults_to_running_without_error():
    ctx = Context(execution_id="e", workflow_id="w", node="a")
    assert ctx.status == ExecutionStatus.RUNNING
    assert ctx.error is None


async def test_completed_run_has_completed_status():
    rt = Runtime(single("ok", {"success": None}), make_registry(("ok", static_node(Result()))))
    ctx = await rt.execute("e1")
    assert ctx.status == ExecutionStatus.COMPLETED


async def test_suspended_run_has_suspended_status():
    wf = Workflow(
        id="w",
        start="gate",
        nodes={
            "gate": Node(type="gate", transitions={"waiting": None, "approved": "done"}),
            "done": Node(type="ok", transitions={"success": None}),
        },
    )
    rt = Runtime(
        wf,
        make_registry(("gate", gate_node()), ("ok", static_node(Result()))),
        store=InMemoryStore(),
        suspend_on=frozenset({"waiting"}),
    )
    ctx = await rt.execute("e1")
    assert ctx.status == ExecutionStatus.SUSPENDED
    resumed = await rt.resume("e1", {"decision": "yes"})
    assert resumed.status == ExecutionStatus.COMPLETED


# --- B. finished runs are persisted; finished runs can't be resumed ---


async def test_completed_run_is_saved_to_store():
    store = InMemoryStore()
    rt = Runtime(
        single("ok", {"success": None}),
        make_registry(("ok", static_node(Result(output={"x": 1})))),
        store=store,
    )
    await rt.execute("e1")
    saved = await store.load("e1")
    assert saved is not None
    assert saved.status == ExecutionStatus.COMPLETED
    assert saved.node is None
    assert saved.data == {"x": 1}


async def test_resume_of_completed_run_raises():
    store = InMemoryStore()
    rt = Runtime(
        single("ok", {"success": None}), make_registry(("ok", static_node(Result()))), store=store
    )
    await rt.execute("e1")
    with pytest.raises(RuntimeError, match="already completed"):
        await rt.resume("e1")


# --- C. failures end the run instead of crashing it ---


async def test_error_without_failure_route_ends_run_as_failed():
    store = InMemoryStore()
    events, on_event = recorder()
    err = NodeError(code="BOOM", message="it broke")
    rt = Runtime(
        single("bad", {"success": None}), make_registry(("bad", static_node(err))), store=store
    )
    ctx = await rt.execute("e1", on_event=on_event)
    assert ctx.status == ExecutionStatus.FAILED
    assert ctx.error is not None and ctx.error.code == "BOOM"
    assert ctx.node == "a"  # where it failed
    assert [e.type for e in events][-1] == EventType.WORKFLOW_FAILED
    assert EventType.WORKFLOW_COMPLETED not in [e.type for e in events]
    assert (await store.load("e1")).status == ExecutionStatus.FAILED


async def test_error_with_failure_route_still_follows_it():
    rt = Runtime(
        Workflow(
            id="w",
            start="a",
            nodes={
                "a": Node(type="bad", transitions={"success": None, "failure": "handler"}),
                "handler": Node(type="ok", transitions={"success": None}),
            },
        ),
        make_registry(
            ("bad", static_node(NodeError(code="X", message="m"))), ("ok", static_node(Result()))
        ),
    )
    ctx = await rt.execute("e1")
    assert ctx.status == ExecutionStatus.COMPLETED
    assert ctx.error is None


async def test_resume_of_failed_run_raises():
    store = InMemoryStore()
    rt = Runtime(
        single("bad", {"success": None}),
        make_registry(("bad", static_node(NodeError(code="X", message="m")))),
        store=store,
    )
    await rt.execute("e1")
    with pytest.raises(RuntimeError, match="already failed"):
        await rt.resume("e1")


async def test_undeclared_success_outcome_still_raises_but_records_failure():
    store = InMemoryStore()
    events, on_event = recorder()
    rt = Runtime(
        single("odd", {"success": None}),
        make_registry(("odd", static_node(Result(transition="surprise")))),
        store=store,
    )
    with pytest.raises(RuntimeError, match="unknown transition 'surprise'"):
        await rt.execute("e1", on_event=on_event)
    assert events[-1].type == EventType.WORKFLOW_FAILED
    saved = await store.load("e1")
    assert saved.status == ExecutionStatus.FAILED
    assert saved.error is not None and saved.error.code == "UNKNOWN_TRANSITION"


# --- D. tracebacks ---


async def test_unexpected_exception_keeps_type_and_traceback():
    rt = Runtime(
        single("boom", {"success": None}),
        make_registry(("boom", raising_node(ValueError("bad value")))),
    )
    ctx = await rt.execute("e1")
    assert ctx.status == ExecutionStatus.FAILED
    assert ctx.error.code == "UNEXPECTED_ERROR"
    assert ctx.error.message == "bad value"
    assert ctx.error.details["exception_type"] == "ValueError"
    assert "raise exc" in ctx.error.details["traceback"]
