import pytest

from workflow_core import InMemoryStore, Runtime
from workflow_core.context import Context
from workflow_core.registry import Registry
from workflow_core.result import NodeError, Result
from workflow_core.store import ExecutionStore
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


def request_aware_node() -> type:
    """Simulates UINode behaviour: GET → render, POST → submitted.
    On submission resets request to GET so the next UI node renders."""
    class _Node:
        async def run(self, context: Context, params: dict) -> Result | NodeError:
            method = context.data.get("request", {}).get("method", "GET")
            if method == "POST":
                return Result(
                    output={
                        "validated": context.data.get("input", {}),
                        "request": {"method": "GET"},   # reset so next ui node renders
                    },
                    transition="submitted",
                )
            return Result(output={"html": f"<form node={context.node}>"}, transition="render")
    return _Node


def linear_ui_workflow() -> Workflow:
    return Workflow(
        id="onboarding",
        start="step1",
        nodes={
            "step1": Node(type="ui", transitions={"render": None, "submitted": "step2", "error": None}),
            "step2": Node(type="ui", transitions={"render": None, "submitted": "done", "error": None}),
            "done":  Node(type="noop", transitions={"success": None}),
        },
    )


# --- ExecutionStore (InMemoryStore) ---

async def test_in_memory_store_save_and_load():
    store = InMemoryStore()
    ctx = Context(execution_id="e1", workflow_id="w1", node="step1", data={})
    await store.save("e1", ctx)
    loaded = await store.load("e1")
    assert loaded is not None
    assert loaded.node == "step1"


async def test_in_memory_store_load_missing_returns_none():
    store = InMemoryStore()
    assert await store.load("nonexistent") is None


async def test_in_memory_store_overwrites_on_second_save():
    store = InMemoryStore()
    ctx1 = Context(execution_id="e1", workflow_id="w1", node="step1", data={})
    ctx2 = Context(execution_id="e1", workflow_id="w1", node="step2", data={})
    await store.save("e1", ctx1)
    await store.save("e1", ctx2)
    loaded = await store.load("e1")
    assert loaded.node == "step2"


# --- Suspension ---

async def test_render_transition_suspends_execution():
    workflow = Workflow(
        id="w",
        start="form",
        nodes={"form": Node(type="ui", transitions={"render": None, "submitted": None})},
    )
    registry = make_registry(("ui", static_node(Result(output={"html": "<form>"}, transition="render"))))
    store = InMemoryStore()
    runtime = Runtime(workflow, registry, store=store)

    context = await runtime.execute("e1", input_data={"request": {"method": "GET"}})

    assert context.node == "form"         # node preserved — not advanced
    assert context.data["html"] == "<form>"


async def test_suspended_context_is_saved_to_store():
    workflow = Workflow(
        id="w",
        start="form",
        nodes={"form": Node(type="ui", transitions={"render": None})},
    )
    registry = make_registry(("ui", static_node(Result(output={"html": "<form>"}, transition="render"))))
    store = InMemoryStore()
    runtime = Runtime(workflow, registry, store=store)

    await runtime.execute("e1")

    saved = await store.load("e1")
    assert saved is not None
    assert saved.node == "form"


async def test_error_transition_also_suspends():
    workflow = Workflow(
        id="w",
        start="form",
        nodes={"form": Node(type="ui", transitions={"error": None})},
    )
    registry = make_registry(("ui", static_node(Result(output={"html": "<err>"}, transition="error"))))
    store = InMemoryStore()
    runtime = Runtime(workflow, registry, store=store)

    context = await runtime.execute("e1")

    assert context.node == "form"
    assert await store.load("e1") is not None


async def test_success_transition_does_not_suspend():
    workflow = Workflow(
        id="w",
        start="step",
        nodes={"step": Node(type="noop", transitions={"success": None})},
    )
    registry = make_registry(("noop", static_node(Result())))
    store = InMemoryStore()
    runtime = Runtime(workflow, registry, store=store)

    context = await runtime.execute("e1")

    assert context.node is None           # workflow completed normally
    assert await store.load("e1") is None  # nothing saved


async def test_no_store_suspend_does_not_fail():
    workflow = Workflow(
        id="w",
        start="form",
        nodes={"form": Node(type="ui", transitions={"render": None})},
    )
    registry = make_registry(("ui", static_node(Result(transition="render"))))
    runtime = Runtime(workflow, registry)  # no store

    context = await runtime.execute("e1")
    assert context.node == "form"         # suspended in memory, not saved


async def test_custom_suspend_on():
    workflow = Workflow(
        id="w",
        start="step",
        nodes={"step": Node(type="noop", transitions={"waiting": None})},
    )
    registry = make_registry(("noop", static_node(Result(transition="waiting"))))
    store = InMemoryStore()
    runtime = Runtime(workflow, registry, store=store, suspend_on=frozenset({"waiting"}))

    context = await runtime.execute("e1")
    assert context.node == "step"
    assert await store.load("e1") is not None


# --- Resume ---

async def test_resume_without_store_raises():
    workflow = Workflow(id="w", start="s", nodes={"s": Node(type="n", transitions={"success": None})})
    registry = make_registry(("n", static_node(Result())))
    runtime = Runtime(workflow, registry)  # no store

    with pytest.raises(RuntimeError, match="no store"):
        await runtime.resume("e1")


async def test_resume_unknown_execution_raises():
    workflow = Workflow(id="w", start="s", nodes={"s": Node(type="n", transitions={"success": None})})
    registry = make_registry(("n", static_node(Result())))
    runtime = Runtime(workflow, registry, store=InMemoryStore())

    with pytest.raises(RuntimeError, match="not found"):
        await runtime.resume("unknown")


async def test_resume_continues_from_saved_node():
    call_count = 0

    class ToggleNode:
        async def run(self, context: Context, params: dict) -> Result:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Result(output={"html": "<form>"}, transition="render")
            return Result(output={"validated": {"x": 1}}, transition="submitted")

    workflow = Workflow(
        id="w",
        start="step1",
        nodes={
            "step1": Node(type="ui", transitions={"render": None, "submitted": "step2"}),
            "step2": Node(type="noop", transitions={"success": None}),
        },
    )
    registry = Registry()
    registry.register("ui")(ToggleNode)
    registry.register("noop")(static_node(Result(output={"done": True})))
    store = InMemoryStore()
    runtime = Runtime(workflow, registry, store=store)

    # first call — suspends at step1
    ctx = await runtime.execute("e1")
    assert ctx.node == "step1"
    assert await store.load("e1") is not None

    # second call — step1 now returns "submitted", advances to step2, completes
    ctx = await runtime.resume("e1")
    assert ctx.node is None
    assert ctx.data.get("done") is True


async def test_resume_merges_new_input_into_saved_context():
    workflow = Workflow(
        id="w",
        start="form",
        nodes={"form": Node(type="ui", transitions={"render": None, "submitted": None})},
    )

    captured: list[Context] = []

    class CapturingNode:
        async def run(self, context: Context, params: dict) -> Result:
            captured.append(context)
            return Result(transition="submitted")

    store = InMemoryStore()
    registry = make_registry(("ui", CapturingNode))
    runtime = Runtime(workflow, registry, store=store)

    # save a context with existing data
    saved = Context(execution_id="e1", workflow_id="w", node="form", data={"name": "Alice"})
    await store.save("e1", saved)

    await runtime.resume("e1", input_data={"request": {"method": "POST"}})

    assert captured[0].data["name"] == "Alice"
    assert captured[0].data["request"]["method"] == "POST"


# --- Multi-step form round-trip ---

async def test_multi_step_form_full_round_trip():
    """GET step1 → suspend. POST step1 → advance to step2 → suspend.
       POST step2 → advance to done → complete."""

    workflow = linear_ui_workflow()
    registry = make_registry(
        ("ui", request_aware_node()),
        ("noop", static_node(Result(output={"finished": True}))),
    )
    store = InMemoryStore()
    runtime = Runtime(workflow, registry, store=store)

    # Request 1: GET step1
    ctx = await runtime.execute("e1", {"request": {"method": "GET"}})
    assert ctx.node == "step1"
    assert "<form" in ctx.data["html"]

    # Request 2: POST step1
    ctx = await runtime.resume("e1", {"request": {"method": "POST"}, "input": {"name": "Alice"}})
    assert ctx.node == "step2"            # advanced past step1
    assert "<form" in ctx.data["html"]    # step2 rendered

    # Request 3: POST step2
    ctx = await runtime.resume("e1", {"request": {"method": "POST"}, "input": {"role": "admin"}})
    assert ctx.node is None               # workflow completed
    assert ctx.data.get("finished") is True


async def test_multi_step_post_failure_stays_at_same_node():
    """POST with invalid data → suspend at same node, errors in context."""

    class FormlikeNode:
        async def run(self, context: Context, params: dict) -> Result | NodeError:
            method = context.data.get("request", {}).get("method", "GET")
            if method == "POST":
                data = context.data.get("input", {})
                if not data.get("name"):
                    return Result(output={"html": "<form errors>", "errors": {"name": "required"}}, transition="error")
                return Result(transition="submitted")
            return Result(output={"html": "<form>"}, transition="render")

    workflow = Workflow(
        id="w",
        start="form",
        nodes={
            "form": Node(type="ui", transitions={"render": None, "submitted": "done", "error": None}),
            "done": Node(type="noop", transitions={"success": None}),
        },
    )
    store = InMemoryStore()
    registry = make_registry(("ui", FormlikeNode), ("noop", static_node(Result())))
    runtime = Runtime(workflow, registry, store=store)

    # GET
    await runtime.execute("e1", {"request": {"method": "GET"}})

    # POST with missing name — should stay at "form"
    ctx = await runtime.resume("e1", {"request": {"method": "POST"}, "input": {}})
    assert ctx.node == "form"
    assert "errors" in ctx.data

    # POST with valid name — should advance
    ctx = await runtime.resume("e1", {"request": {"method": "POST"}, "input": {"name": "Alice"}})
    assert ctx.node is None
