from __future__ import annotations

from typing import Any

import jinja2

from workflow_core.context import Context
from workflow_core.processors import render_template, validate_fields
from workflow_core.result import NodeError, Result


class UINode:
    def __init__(self, env: jinja2.Environment) -> None:
        self._env = env

    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        method = context.data.get("request", {}).get("method", "GET").upper()

        if method == "GET":
            return await self._render(context, params, errors={}, transition="render")

        return await self._submit(context, params)

    async def _submit(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        result = await validate_fields(
            params.get("fields", {}),
            source=params.get("source", "input"),
        )(context)

        if isinstance(result, NodeError):
            return await self._render(context, params, errors=result.details, transition="error")

        return Result(
            output={"validated": result.data.get("validated", {})},
            transition="submitted",
        )

    async def _render(
        self,
        context: Context,
        params: dict[str, Any],
        errors: dict[str, str],
        transition: str,
    ) -> Result | NodeError:
        result = await render_template(
            env=self._env,
            template=params.get("template", ""),
            partial=params.get("partial_template"),
            fields=params.get("fields", {}),
            errors=errors,
        )(context)

        if isinstance(result, NodeError):
            return result

        return Result(output={"html": result.data["html"]}, transition=transition)
