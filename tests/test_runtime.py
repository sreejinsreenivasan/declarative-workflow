import pytest

from workflow_core.context import Context
from workflow_core.event import Event, EventType
from workflow_core.registry import Registry
from workflow_core.result import NodeError, Result
from workflow_core.runtime import Runtime
from workflow_core.workflow import Node, Workflow


# --- helpers ---

def make_registry(*pairs: tuple[str, type]) -> Registry:
    r = Registry()
    for type_name, cls in pairs:
        r.register(type_name)(cls)
    return r


def static_node(result: Result | NodeError) -> type:
    class _Node:
        async def run(self, context: Context, params: dict) -> Result | NodeError:
            return result

    return _Node


def capturing_node(captured: list) -> type:
    class _Node:
        async def run(self, context: Context, params: dict) -> Result:
            captured.append({"context": context, "params": params})
            return Result()

    return _Node


def raising_node() -> type:
    class _Node:
        async def run(self, context: Context, params: dict) -> Result:
            raise ValueError("boom")

    return _Node


# --- single node ---

async def test_single_node_completes():
    workflow = Workflow(
        id="w",
        start="step",
        nodes={"step": Node(type="noop", transitions={"success": None})},
    )
    registry = make_registry(("noop", static_node(Result())))
    context = await Runtime(workflow, registry).execute("e1")
    assert context.node is None


async def test_output_merged_into_context():
    workflow = Workflow(
        id="w",
        start="step",
        nodes={"step": Node(type="noop", transitions={"success": None})},
    )
    registry = make_registry(("noop", static_node(Result(output={"user_id": 42}))))
    context = await Runtime(workflow, registry).execute("e1")
    assert context.data["user_id"] == 42


async def test_input_data_available_in_context():
    captured: list = []
    workflow = Workflow(
        id="w",
        start="step",
        nodes={"step": Node(type="noop", transitions={"success": None})},
    )
    registry = make_registry(("noop", capturing_node(captured)))
    await Runtime(workflow, registry).execute("e1", input_data={"name": "Alice"})
    assert captured[0]["context"].data["name"] == "Alice"


async def test_params_passed_to_node():
    captured: list = []
    workflow = Workflow(
        id="w",
        start="step",
        nodes={"step": Node(type="noop", params={"url": "https://x.com"}, transitions={"success": None})},
    )
    registry = make_registry(("noop", capturing_node(captured)))
    await Runtime(workflow, registry).execute("e1")
    assert captured[0]["params"]["url"] == "https://x.com"


# --- multi-node ---

async def test_linear_workflow_traverses_all_nodes():
    visited: list = []

    class TrackingNode:
        async def run(self, context: Context, params: dict) -> Result:
            visited.append(context.node)
            return Result()

    workflow = Workflow(
        id="w",
        start="a",
        nodes={
            "a": Node(type="t", transitions={"success": "b"}),
            "b": Node(type="t", transitions={"success": "c"}),
            "c": Node(type="t", transitions={"success": None}),
        },
    )
    registry = make_registry(("t", TrackingNode))
    await Runtime(workflow, registry).execute("e1")
    assert visited == ["a", "b", "c"]


async def test_output_accumulates_across_nodes():
    workflow = Workflow(
        id="w",
        start="a",
        nodes={
            "a": Node(type="t", transitions={"success": "b"}),
            "b": Node(type="t", transitions={"success": None}),
        },
    )

    call_count = 0

    class CountingNode:
        async def run(self, context: Context, params: dict) -> Result:
            nonlocal call_count
            call_count += 1
            return Result(output={f"step_{call_count}": True})

    registry = make_registry(("t", CountingNode))
    context = await Runtime(workflow, registry).execute("e1")
    assert context.data["step_1"] is True
    assert context.data["step_2"] is True


# --- branching ---

async def test_decision_routes_success_branch():
    workflow = Workflow(
        id="w",
        start="gate",
        nodes={
            "gate": Node(type="decision", transitions={"yes": "ok", "no": "fail"}),
            "ok": Node(type="terminal", transitions={"success": None}),
            "fail": Node(type="terminal", transitions={"success": None}),
        },
    )
    visited: list = []

    class DecisionNode:
        async def run(self, context: Context, params: dict) -> Result:
            return Result(transition="yes")

    class TerminalNode:
        async def run(self, context: Context, params: dict) -> Result:
            visited.append(context.node)
            return Result()

    registry = make_registry(("decision", DecisionNode), ("terminal", TerminalNode))
    await Runtime(workflow, registry).execute("e1")
    assert visited == ["ok"]


# --- error handling ---

async def test_node_error_follows_failure_transition():
    workflow = Workflow(
        id="w",
        start="step",
        nodes={"step": Node(type="noop", transitions={"failure": None})},
    )
    registry = make_registry(("noop", static_node(NodeError(code="ERR", message="fail"))))
    context = await Runtime(workflow, registry).execute("e1")
    assert context.node is None


async def test_raising_node_wrapped_as_node_error():
    workflow = Workflow(
        id="w",
        start="step",
        nodes={"step": Node(type="boom", transitions={"failure": None})},
    )
    registry = make_registry(("boom", raising_node()))
    context = await Runtime(workflow, registry).execute("e1")
    assert context.node is None


async def test_unknown_transition_raises():
    workflow = Workflow(
        id="w",
        start="step",
        nodes={"step": Node(type="noop", transitions={"success": None})},
    )
    registry = make_registry(("noop", static_node(Result(transition="unknown"))))
    with pytest.raises(RuntimeError, match="unknown transition 'unknown'"):
        await Runtime(workflow, registry).execute("e1")


# --- events ---

async def test_events_emitted_in_order():
    workflow = Workflow(
        id="w",
        start="step",
        nodes={"step": Node(type="noop", transitions={"success": None})},
    )
    registry = make_registry(("noop", static_node(Result())))
    events: list[Event] = []
    await Runtime(workflow, registry).execute("e1", on_event=events.append)

    types = [e.type for e in events]
    assert types == [
        EventType.NODE_STARTED,
        EventType.NODE_COMPLETED,
        EventType.TRANSITION_SELECTED,
        EventType.WORKFLOW_COMPLETED,
    ]


async def test_events_carry_correct_node_id():
    workflow = Workflow(
        id="w",
        start="my_step",
        nodes={"my_step": Node(type="noop", transitions={"success": None})},
    )
    registry = make_registry(("noop", static_node(Result())))
    events: list[Event] = []
    await Runtime(workflow, registry).execute("e1", on_event=events.append)

    node_events = [e for e in events if e.node_id is not None]
    assert all(e.node_id == "my_step" for e in node_events)


async def test_async_event_handler_is_awaited():
    workflow = Workflow(
        id="w",
        start="step",
        nodes={"step": Node(type="noop", transitions={"success": None})},
    )
    registry = make_registry(("noop", static_node(Result())))
    events: list[Event] = []

    async def async_handler(event: Event) -> None:
        events.append(event)

    await Runtime(workflow, registry).execute("e1", on_event=async_handler)
    assert len(events) == 4
