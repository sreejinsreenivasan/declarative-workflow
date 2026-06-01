from __future__ import annotations

from typing import Any

import jinja2

from workflow_core.context import Context
from workflow_core.nodes.form import _validate_field
from workflow_core.result import NodeError, Result


class UINode:
    def __init__(self, env: jinja2.Environment) -> None:
        self._env = env

    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        method = context.data.get("request", {}).get("method", "GET").upper()

        if method == "GET":
            return self._render(context, params, errors={}, transition="render")

        return self._submit(context, params)

    def _submit(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        fields = params.get("fields", {})
        source = params.get("source", "input")
        data = context.data.get(source) or {}

        errors = {
            name: msg
            for name, rules in fields.items()
            if (msg := _validate_field(name, data.get(name), rules)) is not None
        }

        if errors:
            return self._render(context, params, errors=errors, transition="error")

        validated = {name: data[name] for name in fields if name in data}
        return Result(output={"validated": validated}, transition="submitted")

    def _render(
        self,
        context: Context,
        params: dict[str, Any],
        errors: dict[str, str],
        transition: str,
    ) -> Result | NodeError:
        is_htmx = context.data.get("request", {}).get("is_htmx", False)
        use_partial = is_htmx and "partial_template" in params
        template_path = params.get("partial_template" if use_partial else "template")

        if not template_path:
            return NodeError(code="INVALID_PARAMS", message="'template' is required")

        try:
            template = self._env.get_template(template_path)
        except jinja2.TemplateNotFound:
            return NodeError(
                code="TEMPLATE_NOT_FOUND",
                message=f"Template '{template_path}' not found",
            )

        html = template.render(
            data=context.data,
            fields=params.get("fields", {}),
            errors=errors,
            execution_id=context.execution_id,
            node=context.node,
        )

        return Result(output={"html": html}, transition=transition)
