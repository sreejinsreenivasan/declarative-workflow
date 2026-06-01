from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workflow_core.context import Context
from workflow_core.nodes.http import HTTPNode
from workflow_core.result import NodeError, Result


def ctx(data: dict | None = None) -> Context:
    return Context(execution_id="e1", workflow_id="w1", node="http", data=data or {})


def mock_response(status_code: int, json_data: dict) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.is_error = status_code >= 400
    response.json.return_value = json_data
    return response


async def test_successful_get_request():
    with patch("workflow_core.processors.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response(200, {"id": 1}))
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await HTTPNode().run(ctx(), {"method": "GET", "url": "https://example.com/api"})

    assert isinstance(result, Result)
    assert result.output["http_response"] == {"id": 1}


async def test_post_with_body_from_context():
    with patch("workflow_core.processors.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response(201, {"created": True}))
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await HTTPNode().run(
            ctx({"validated": {"name": "Alice"}}),
            {"method": "POST", "url": "https://example.com/users", "body_key": "validated"},
        )
        _, kwargs = mock_client.request.call_args
        assert kwargs["json"] == {"name": "Alice"}

    assert isinstance(result, Result)


async def test_custom_response_key():
    with patch("workflow_core.processors.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response(200, {"status": "ok"}))
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await HTTPNode().run(
            ctx(),
            {"method": "GET", "url": "https://example.com", "response_key": "kyc_result"},
        )

    assert "kyc_result" in result.output


async def test_http_4xx_returns_error():
    with patch("workflow_core.processors.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response(404, {}))
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await HTTPNode().run(ctx(), {"method": "GET", "url": "https://example.com"})

    assert isinstance(result, NodeError)
    assert result.code == "HTTP_ERROR"
    assert result.details["status_code"] == 404


async def test_http_5xx_returns_error():
    with patch("workflow_core.processors.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response(500, {}))
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await HTTPNode().run(ctx(), {"method": "GET", "url": "https://example.com"})

    assert isinstance(result, NodeError)
    assert result.code == "HTTP_ERROR"


async def test_connection_error_returns_error():
    import httpx as _httpx

    with patch("workflow_core.processors.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=_httpx.ConnectError("refused"))
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await HTTPNode().run(ctx(), {"method": "GET", "url": "https://gone.example.com"})

    assert isinstance(result, NodeError)
    assert result.code == "CONNECTION_ERROR"


async def test_missing_url_returns_error():
    result = await HTTPNode().run(ctx(), {"method": "GET"})
    assert isinstance(result, NodeError)
    assert result.code == "INVALID_PARAMS"
