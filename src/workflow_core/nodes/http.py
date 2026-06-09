from __future__ import annotations

from typing import Any

from workflow_core.context import Context
from workflow_core.processors import HttpMethod, call_http
from workflow_core.result import NodeError, Result


class HTTPNode:
    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:  # params: caller-defined node config
        url = params.get("url")
        if not url:
            return NodeError(code="INVALID_PARAMS", message="'url' is required")

        raw_method = str(params.get("method", "GET")).upper()
        try:
            method = HttpMethod(raw_method)
        except ValueError:
            return NodeError(code="INVALID_PARAMS", message=f"Unknown HTTP method '{raw_method}'")

        response_key = params.get("response_key", "http_response")

        result = await call_http(
            method=method,
            url=url,
            body_key=params.get("body_key"),
            response_key=response_key,
            headers=params.get("headers"),
        )(context)

        if isinstance(result, NodeError):
            return result

        return Result(output={response_key: result.data[response_key]})
