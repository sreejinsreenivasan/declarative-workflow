from __future__ import annotations

from typing import TYPE_CHECKING

from workflow_core.event import Event, EventType, OnEvent

if TYPE_CHECKING:
    from opentelemetry.trace import Span, Tracer


def make_otel_handler(tracer: Tracer) -> OnEvent:
    """
    Return an async OnEvent callback that records an OpenTelemetry span for
    each node execution.

    Spans attach to the active span context at call time — e.g. a root span
    set by ``opentelemetry-instrumentation-fastapi`` — so they appear as
    children automatically.

    Attributes per span:

    - ``workflow.execution_id``
    - ``workflow.node_id``
    - ``workflow.transition``  (added on NODE_COMPLETED)

    Requires the ``otel`` extra::

        pip install 'workflow-core[otel]'

    Usage::

        from opentelemetry import trace
        from workflow_core.adapters.otel import make_otel_handler

        tracer = trace.get_tracer(__name__)
        handler = make_otel_handler(tracer)
        await runtime.execute("exec-001", data, on_event=handler)
    """
    try:
        from opentelemetry.trace import StatusCode
    except ImportError as exc:
        raise ImportError(
            "opentelemetry-api is required for this adapter. "
            "Install it with: pip install 'workflow-core[otel]'"
        ) from exc

    _spans: dict[str, Span] = {}  # "{execution_id}:{node_id}" → active Span

    async def _handler(event: Event) -> None:
        node_id = event.node_id or "unknown"
        key = f"{event.execution_id}:{node_id}"

        if event.type == EventType.NODE_STARTED:
            _spans[key] = tracer.start_span(
                f"workflow.node.{node_id}",
                attributes={
                    "workflow.execution_id": event.execution_id,
                    "workflow.node_id": node_id,
                },
            )

        elif event.type == EventType.NODE_COMPLETED:
            span = _spans.pop(key, None)
            if span is not None:
                span.set_attribute("workflow.transition", event.data.get("transition", ""))
                span.end()

        elif event.type == EventType.WORKFLOW_FAILED:
            for k in [k for k in _spans if k.startswith(f"{event.execution_id}:")]:
                span = _spans.pop(k)
                span.set_status(StatusCode.ERROR)
                span.end()

    return _handler
