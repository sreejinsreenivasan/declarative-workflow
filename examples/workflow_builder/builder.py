"""
Workflow Builder — custom nodes, SchemaNode, and workflow definition.

The builder is itself a workflow:

  workflow_meta → init_builder → add_node ⇄ accumulate_node → review
"""
from __future__ import annotations

import json
from typing import Any, Callable

import jinja2  # type: ignore[import-untyped]

from workflow_core import Node, NodeError, Registry, Result, Workflow
from workflow_core.context import Context
from workflow_core.nodes.decision import DecisionNode
from workflow_core.nodes.form import FormNode
from workflow_core.nodes.http import HTTPNode
from workflow_core.nodes.response import ResponseNode
from workflow_core.nodes.transform import TransformNode
from workflow_core.processors import validate_fields
from workflow_core.ui.loader import ComponentLoader

NODE_TYPES = ["form", "decision", "http", "transform", "persist", "response", "ui"]

# Page factory type: (execution_id, data, errors) → Component
PageFactory = Callable[[str, dict[str, Any], dict[str, str]], Any]


# ---------------------------------------------------------------------------
# SchemaNode — renders a component page, validates form on POST
# ---------------------------------------------------------------------------

class SchemaNode:
    """
    Drop-in replacement for UINode when you want Python-defined page schemas
    instead of Jinja2 template files.

    ``page_factory``  — callable returning a Page component tree
    ``fields``        — same field config dict used by validate_fields
    ``env``           — Jinja2 environment for the full-page base layout (optional)
    """

    def __init__(
        self,
        page_factory: PageFactory,
        fields: dict[str, Any],
        loader: ComponentLoader | None = None,
        env: jinja2.Environment | None = None,
    ) -> None:
        self._page_factory = page_factory
        self._fields = fields
        self._loader = loader or ComponentLoader()
        self._env = env

    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        method = context.data.get("request", {}).get("method", "GET").upper()
        is_htmx = context.data.get("request", {}).get("is_htmx", False)

        if method == "GET":
            return self._render(context, {}, "render", is_htmx)
        return await self._submit(context, is_htmx)

    async def _submit(self, context: Context, is_htmx: bool) -> Result | NodeError:
        result = await validate_fields(self._fields)(context)
        if isinstance(result, NodeError):
            return self._render(context, result.details, "error", is_htmx)
        validated = result.data.get("validated", {})
        return Result(output={"validated": validated}, transition="submitted")

    def _render(
        self,
        context: Context,
        errors: dict[str, str],
        transition: str,
        is_htmx: bool,
    ) -> Result:
        page = self._page_factory(context.execution_id, context.data, errors)
        content_html = self._loader.render(page, execution_id=context.execution_id, errors=errors)

        if not is_htmx and self._env is not None:
            tmpl = self._env.get_template("base.html")
            html = tmpl.render(content=content_html, execution_id=context.execution_id)
        else:
            html = content_html

        return Result(output={"html": html}, transition=transition)


# ---------------------------------------------------------------------------
# Custom nodes
# ---------------------------------------------------------------------------

class InitBuilderNode:
    """Copy validated.workflow_id into builder state; reset request to GET."""

    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:  # noqa: ARG002
        validated = context.data.get("validated", {})
        workflow_id = validated.get("workflow_id", "").strip()
        if not workflow_id:
            return NodeError(code="MISSING_WORKFLOW_ID", message="workflow_id is required")
        builder = {"id": workflow_id, "start": None, "nodes": {}}
        return Result(
            output={"builder": builder, "request": {"method": "GET"}, "input": {}},
            transition="success",
        )


class AccumulateNode:
    """
    Append the submitted node config to builder.nodes.
    Reset request/input to GET so the next SchemaNode renders instead of resubmits.
    Transitions on validated._action: "add_more" or "done".
    """

    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:  # noqa: ARG002
        validated = context.data.get("validated", {})
        builder: dict[str, Any] = context.data.get(
            "builder", {"id": "workflow", "start": None, "nodes": {}}
        )

        node_id = validated.get("node_id", "").strip()
        node_type = validated.get("node_type", "").strip()
        action = validated.get("_action", "add_more")

        if not node_id:
            return NodeError(code="MISSING_NODE_ID", message="node_id is required")
        if node_type not in NODE_TYPES:
            return NodeError(
                code="INVALID_NODE_TYPE",
                message=f"type must be one of {NODE_TYPES}",
            )

        try:
            node_params = json.loads(validated.get("params_json") or "{}")
        except json.JSONDecodeError as exc:
            return NodeError(code="INVALID_PARAMS_JSON", message=f"params_json: {exc}")

        try:
            node_transitions = json.loads(validated.get("transitions_json") or "{}")
        except json.JSONDecodeError as exc:
            return NodeError(code="INVALID_TRANSITIONS_JSON", message=f"transitions_json: {exc}")

        existing_nodes: dict[str, Any] = builder.get("nodes", {})
        nodes = {**existing_nodes, node_id: {
            "type": node_type,
            "params": node_params,
            "transitions": node_transitions,
        }}
        start = builder.get("start") or node_id  # first added becomes start

        new_builder = {**builder, "start": start, "nodes": nodes}
        return Result(
            output={"builder": new_builder, "request": {"method": "GET"}, "input": {}},
            transition=action,
        )


# ---------------------------------------------------------------------------
# Workflow definition
# ---------------------------------------------------------------------------

BUILDER_WORKFLOW = Workflow(
    id="workflow_builder",
    start="workflow_meta",
    nodes={
        "workflow_meta": Node(
            type="workflow_meta_schema",
            params={
                "fields": {"workflow_id": {"type": "str", "required": True}},
            },
            transitions={"render": None, "error": None, "submitted": "init_builder"},
        ),
        "init_builder": Node(
            type="init_builder",
            transitions={"success": "add_node"},
        ),
        "add_node": Node(
            type="add_node_schema",
            params={
                "fields": {
                    "node_id":          {"type": "str", "required": True},
                    "node_type":        {"type": "str", "required": True},
                    "params_json":      {"type": "str", "required": False},
                    "transitions_json": {"type": "str", "required": False},
                    "_action":          {"type": "str", "required": True},
                },
            },
            transitions={"render": None, "error": None, "submitted": "accumulate_node"},
        ),
        "accumulate_node": Node(
            type="accumulate_node",
            transitions={"add_more": "add_node", "done": "review"},
        ),
        "review": Node(
            type="review_schema",
            params={"fields": {}},
            transitions={"render": None, "error": None, "submitted": None},
        ),
    },
)


# ---------------------------------------------------------------------------
# Registry factory
# ---------------------------------------------------------------------------

def create_registry(env: jinja2.Environment) -> Registry:  # type: ignore[misc]
    from examples.workflow_builder.pages import (
        add_node_page,
        review_page,
        workflow_meta_page,
    )

    loader = ComponentLoader()

    _page_map: dict[str, PageFactory] = {
        "workflow_meta": workflow_meta_page,
        "add_node":      add_node_page,
        "review":        review_page,
    }

    def _make_schema_node(node_id: str) -> type:
        page_fn = _page_map[node_id]

        class _SchemaNode(SchemaNode):
            def __init__(self) -> None:
                node_def = BUILDER_WORKFLOW.nodes[node_id]
                super().__init__(
                    page_factory=page_fn,
                    fields=node_def.params.get("fields", {}),
                    loader=loader,
                    env=env,
                )

        _SchemaNode.__name__ = f"SchemaNode_{node_id}"
        return _SchemaNode

    registry = Registry()

    registry.register("workflow_meta_schema")(_make_schema_node("workflow_meta"))
    registry.register("add_node_schema")(_make_schema_node("add_node"))
    registry.register("review_schema")(_make_schema_node("review"))
    registry.register("init_builder")(InitBuilderNode)
    registry.register("accumulate_node")(AccumulateNode)
    registry.register("form")(FormNode)
    registry.register("decision")(DecisionNode)
    registry.register("http")(HTTPNode)
    registry.register("transform")(TransformNode)
    registry.register("response")(ResponseNode)

    return registry
