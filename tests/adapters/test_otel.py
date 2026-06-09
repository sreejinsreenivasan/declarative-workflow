from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from workflow_core.adapters.otel import make_otel_handler
from workflow_core.event import Event, EventType


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _started(execution_id: str, node_id: str) -> Event:
    return Event(type=EventType.NODE_STARTED, execution_id=execution_id, node_id=node_id)


def _completed(execution_id: str, node_id: str, transition: str = "success") -> Event:
    return Event(
        type=EventType.NODE_COMPLETED,
        execution_id=execution_id,
        node_id=node_id,
        data={"transition": transition},
    )


def _failed(execution_id: str) -> Event:
    return Event(type=EventType.WORKFLOW_FAILED, execution_id=execution_id)


def _mock_tracer() -> tuple[MagicMock, MagicMock]:
    span = MagicMock()
    tracer = MagicMock()
    tracer.start_span.return_value = span
    return tracer, span


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

async def test_node_started_creates_span_with_attributes():
    tracer, span = _mock_tracer()
    handler = make_otel_handler(tracer)

    await handler(_started("exec-1", "validate"))

    tracer.start_span.assert_called_once_with(
        "workflow.node.validate",
        attributes={
            "workflow.execution_id": "exec-1",
            "workflow.node_id": "validate",
        },
    )


async def test_node_completed_ends_span_and_records_transition():
    tracer, span = _mock_tracer()
    handler = make_otel_handler(tracer)

    await handler(_started("exec-1", "validate"))
    await handler(_completed("exec-1", "validate", "success"))

    span.set_attribute.assert_called_once_with("workflow.transition", "success")
    span.end.assert_called_once()


async def test_node_completed_without_prior_started_does_not_raise():
    tracer, _ = _mock_tracer()
    handler = make_otel_handler(tracer)

    await handler(_completed("exec-orphan", "validate"))  # no prior NODE_STARTED


async def test_multiple_nodes_in_sequence_each_get_their_own_span():
    tracer = MagicMock()
    span_a, span_b = MagicMock(), MagicMock()
    tracer.start_span.side_effect = [span_a, span_b]

    handler = make_otel_handler(tracer)
    await handler(_started("exec-1", "node_a"))
    await handler(_completed("exec-1", "node_a", "success"))
    await handler(_started("exec-1", "node_b"))
    await handler(_completed("exec-1", "node_b", "done"))

    span_a.end.assert_called_once()
    span_b.end.assert_called_once()


async def test_concurrent_executions_do_not_share_spans():
    tracer = MagicMock()
    span_1, span_2 = MagicMock(), MagicMock()
    tracer.start_span.side_effect = [span_1, span_2]

    handler = make_otel_handler(tracer)
    await handler(_started("exec-1", "node_a"))
    await handler(_started("exec-2", "node_a"))
    await handler(_completed("exec-1", "node_a", "success"))

    span_1.end.assert_called_once()
    span_2.end.assert_not_called()


async def test_workflow_failed_ends_dangling_spans_with_error_status():
    from opentelemetry.trace import StatusCode

    tracer, span = _mock_tracer()
    handler = make_otel_handler(tracer)

    await handler(_started("exec-1", "node_a"))
    await handler(_failed("exec-1"))

    span.set_status.assert_called_once_with(StatusCode.ERROR)
    span.end.assert_called_once()


async def test_workflow_failed_only_closes_spans_for_that_execution():
    tracer = MagicMock()
    span_1, span_2 = MagicMock(), MagicMock()
    tracer.start_span.side_effect = [span_1, span_2]

    handler = make_otel_handler(tracer)
    await handler(_started("exec-1", "node_a"))
    await handler(_started("exec-2", "node_b"))
    await handler(_failed("exec-1"))

    span_1.end.assert_called_once()
    span_2.end.assert_not_called()


async def test_handler_is_reusable_across_execute_and_resume():
    tracer = MagicMock()
    span_1, span_2, span_3 = MagicMock(), MagicMock(), MagicMock()
    tracer.start_span.side_effect = [span_1, span_2, span_3]

    handler = make_otel_handler(tracer)

    # first execute() run: nodes A and B, then suspend
    await handler(_started("exec-1", "node_a"))
    await handler(_completed("exec-1", "node_a", "success"))
    await handler(_started("exec-1", "node_b"))
    await handler(_completed("exec-1", "node_b", "render"))

    # resume() run: node C continues
    await handler(_started("exec-1", "node_c"))
    await handler(_completed("exec-1", "node_c", "success"))

    assert tracer.start_span.call_count == 3
    span_1.end.assert_called_once()
    span_2.end.assert_called_once()
    span_3.end.assert_called_once()
