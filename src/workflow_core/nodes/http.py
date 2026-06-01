from __future__ import annotations

from typing import Any

from workflow_core.context import Context
from workflow_core.processors import call_http
from workflow_core.result import NodeError, Result


class HTTPNode:
    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        url = params.get("url")
        if not url:
            return NodeError(code="INVALID_PARAMS", message="'url' is required")

        response_key = params.get("response_key", "http_response")

        result = await call_http(
            method=params.get("method", "GET"),
            url=url,
            body_key=params.get("body_key"),
            response_key=response_key,
            headers=params.get("headers"),
        )(context)

        if isinstance(result, NodeError):
            return result

        return Result(output={response_key: result.data[response_key]})
