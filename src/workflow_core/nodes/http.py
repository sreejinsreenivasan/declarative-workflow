from __future__ import annotations

from typing import Any

import httpx

from workflow_core.context import Context
from workflow_core.result import NodeError, Result


class HTTPNode:
    async def run(self, context: Context, params: dict[str, Any]) -> Result | NodeError:
        method = params.get("method", "GET")
        url = params.get("url")
        body_key = params.get("body_key")
        response_key = params.get("response_key", "http_response")
        headers = params.get("headers", {})

        if not url:
            return NodeError(code="INVALID_PARAMS", message="'url' is required")

        body = context.data.get(body_key) if body_key else None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=body,
                    headers=headers,
                )
        except httpx.ConnectError as exc:
            return NodeError(code="CONNECTION_ERROR", message=str(exc), details={"url": url})

        if response.is_error:
            return NodeError(
                code="HTTP_ERROR",
                message=f"HTTP {response.status_code}",
                details={"status_code": response.status_code, "url": url},
            )

        return Result(output={response_key: response.json()})
