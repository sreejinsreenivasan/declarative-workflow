from __future__ import annotations

import inspect
import traceback
from typing import TYPE_CHECKING, Any

from workflow_core.context import Context, ExecutionStatus
from workflow_core.event import Event, EventType, OnEvent
from workflow_core.registry import Registry
from workflow_core.result import NodeError, Result
from workflow_core.workflow import Workflow

if TYPE_CHECKING:
    from workflow_core.store import ExecutionStore

_DEFAULT_SUSPEND_ON: frozenset[str] = frozenset({"render", "error"})
_FINISHED: frozenset[ExecutionStatus] = frozenset(
    {ExecutionStatus.COMPLETED, ExecutionStatus.FAILED}
)


class UnknownTransition(RuntimeError):
    """A node returned an outcome its definition doesn't declare: a workflow definition bug."""

    def __init__(self, node_id: str, transition: str) -> None:
        super().__init__(f"node '{node_id}': unknown transition '{transition}'")
        self.error = NodeError(
            code="UNKNOWN_TRANSITION",
            message=str(self),
            details={"node": node_id, "transition": transition},
        )


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
        """Continue a suspended execution. The node it suspended at runs again with the
        merged input, so a node can decide whether it now has what it waited for."""
        if not self._store:
            raise RuntimeError("Runtime has no store — cannot resume executions")
        context = await self._store.load(execution_id)
        if context is None:
            raise RuntimeError(f"Execution '{execution_id}' not found")
        if context.status in _FINISHED:
            raise RuntimeError(f"Execution '{execution_id}' already {context.status.value}")
        context = context.merge(input_data or {}).evolve(status=ExecutionStatus.RUNNING)
        return await self._run(context, on_event)

    async def _run(self, context: Context, on_event: OnEvent | None) -> Context:
        while context.node is not None:
            try:
                result, next_node = await self._step(context, on_event)
            except UnknownTransition as exc:
                failed = context.evolve(status=ExecutionStatus.FAILED, error=exc.error)
                await self._finish(failed, on_event)
                raise

            if isinstance(result, NodeError) and not _declared(self.workflow, context, result):
                # An error with no route for it ends the run as FAILED instead of crashing it.
                failed = context.evolve(status=ExecutionStatus.FAILED, error=result)
                return await self._finish(failed, on_event)

            output = result.output if isinstance(result, Result) else {}

            if result.transition in self._suspend_on:
                context = context.merge(output).evolve(status=ExecutionStatus.SUSPENDED)
                if self._store:
                    await self._store.save(context.execution_id, context)
                return context

            context = context.merge(output).evolve(node=next_node)

        return await self._finish(context.evolve(status=ExecutionStatus.COMPLETED), on_event)

    async def _finish(self, context: Context, on_event: OnEvent | None) -> Context:
        """Persist a finished execution and announce how it ended."""
        if self._store:
            await self._store.save(context.execution_id, context)
        if context.status == ExecutionStatus.FAILED:
            event = Event(
                type=EventType.WORKFLOW_FAILED,
                execution_id=context.execution_id,
                node_id=context.node,
                data={"error": context.error.model_dump()} if context.error else {},
            )
        else:
            event = Event(type=EventType.WORKFLOW_COMPLETED, execution_id=context.execution_id)
        await _emit(on_event, event)
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
            if isinstance(result, NodeError):
                return result, None  # _run ends the execution as FAILED
            raise UnknownTransition(node_id, result.transition)  # type: ignore[arg-type]

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


def _declared(workflow: Workflow, context: Context, result: Result | NodeError) -> bool:
    return result.transition in workflow.nodes[context.node].transitions  # type: ignore[index]


async def _run_node(node_cls: type, context: Context, params: dict[str, Any]) -> Result | NodeError:
    try:
        return await node_cls().run(context, params)
    except Exception as exc:
        return NodeError(
            code="UNEXPECTED_ERROR",
            message=str(exc),
            details={"exception_type": type(exc).__name__, "traceback": traceback.format_exc()},
        )


async def _emit(on_event: OnEvent | None, event: Event) -> None:
    if on_event is None:
        return
    if inspect.iscoroutinefunction(on_event):
        await on_event(event)
    else:
        on_event(event)  # type: ignore[arg-type]
