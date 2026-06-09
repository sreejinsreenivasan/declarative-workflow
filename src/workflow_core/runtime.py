from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from workflow_core.context import Context
from workflow_core.event import Event, EventType, OnEvent
from workflow_core.registry import Registry
from workflow_core.result import NodeError, Result
from workflow_core.workflow import Workflow

if TYPE_CHECKING:
    from workflow_core.store import ExecutionStore

_DEFAULT_SUSPEND_ON: frozenset[str] = frozenset({"render", "error"})


class Runtime:
    def __init__(
        self,
        workflow: Workflow,
        registry: Registry,
        store: ExecutionStore | None = None,
        suspend_on: frozenset[str] = _DEFAULT_SUSPEND_ON,
    ) -> None:
        self.workflow = workflow
        self.registry = registry
        self._store = store
        self._suspend_on = suspend_on

    async def execute(
        self,
        execution_id: str,
        input_data: dict[str, Any] | None = None,
        on_event: OnEvent | None = None,
    ) -> Context:
        context = Context(
            execution_id=execution_id,
            workflow_id=self.workflow.id,
            node=self.workflow.start,
            data=input_data or {},
        )
        return await self._run(context, on_event)

    async def resume(
        self,
        execution_id: str,
        input_data: dict[str, Any] | None = None,
        on_event: OnEvent | None = None,
    ) -> Context:
        if not self._store:
            raise RuntimeError("Runtime has no store — cannot resume executions")
        context = await self._store.load(execution_id)
        if context is None:
            raise RuntimeError(f"Execution '{execution_id}' not found")
        return await self._run(context.merge(input_data or {}), on_event)

    async def _run(self, context: Context, on_event: OnEvent | None) -> Context:
        while context.node is not None:
            result, next_node = await self._step(context, on_event)
            output = result.output if isinstance(result, Result) else {}

            if result.transition in self._suspend_on:
                context = context.merge(output)
                if self._store:
                    await self._store.save(context.execution_id, context)
                return context

            context = context.merge(output).evolve(node=next_node)

        await _emit(
            on_event,
            Event(type=EventType.WORKFLOW_COMPLETED, execution_id=context.execution_id),
        )
        return context

    async def _step(
        self,
        context: Context,
        on_event: OnEvent | None,
    ) -> tuple[Result | NodeError, str | None]:
        node_id = context.node
        node_def = self.workflow.nodes[node_id]  # type: ignore[index]

        await _emit(
            on_event,
            Event(type=EventType.NODE_STARTED, execution_id=context.execution_id, node_id=node_id),
        )

        result = await _run_node(self.registry.resolve(node_def.type), context, node_def.params)

        await _emit(
            on_event,
            Event(
                type=EventType.NODE_COMPLETED,
                execution_id=context.execution_id,
                node_id=node_id,
                data={"transition": result.transition},
            ),
        )

        if result.transition not in node_def.transitions:
            raise RuntimeError(f"node '{node_id}': unknown transition '{result.transition}'")

        next_node = node_def.transitions[result.transition]

        await _emit(
            on_event,
            Event(
                type=EventType.TRANSITION_SELECTED,
                execution_id=context.execution_id,
                node_id=node_id,
                data={"transition": result.transition, "next": next_node},
            ),
        )

        return result, next_node


async def _run_node(node_cls: type, context: Context, params: dict[str, Any]) -> Result | NodeError:
    try:
        return await node_cls().run(context, params)
    except Exception as exc:
        return NodeError(code="UNEXPECTED_ERROR", message=str(exc))


async def _emit(on_event: OnEvent | None, event: Event) -> None:
    if on_event is None:
        return
    if inspect.iscoroutinefunction(on_event):
        await on_event(event)
    else:
        on_event(event)  # type: ignore[arg-type]
