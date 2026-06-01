# HTTPNode

Makes an async outbound HTTP request using `httpx`.

```python
from workflow_core.nodes import HTTPNode
registry.register("http")(HTTPNode)
```

---

## Params

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `url` | `str` | required | Request URL |
| `method` | `str` | `"GET"` | HTTP method: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `body_key` | `str \| None` | `None` | `context.data` key to use as JSON request body |
| `response_key` | `str` | `"http_response"` | `context.data` key where response JSON is stored |
| `headers` | `dict[str, str]` | `{}` | Request headers |

---

## Transitions

| Key | When |
|-----|------|
| `"success"` | HTTP 2xx response |
| `"failure"` | HTTP 4xx/5xx response, connection error, or missing `url` |

---

## Output (on success)

```python
Result(output={"http_response": { ...response JSON... }})
```

Use `response_key` to store under a different name:

```python
params={"response_key": "kyc_result"}
# → Result(output={"kyc_result": {...}})
```

## Output (on failure)

```python
# HTTP error
NodeError(code="HTTP_ERROR", message="HTTP 422", details={"status_code": 422, "url": "..."})

# Network error
NodeError(code="CONNECTION_ERROR", message="...", details={"url": "..."})

# Missing URL
NodeError(code="INVALID_PARAMS", message="'url' is required")
```

---

## Examples

```python
# POST with body from context
Node(
    type="http",
    params={
        "method": "POST",
        "url": "https://kyc.example.com/verify",
        "body_key": "validated",
        "response_key": "kyc_result",
        "headers": {"Authorization": "Bearer secret"},
    },
    transitions={"success": "check_kyc_status", "failure": "kyc_error"},
)

# GET request
Node(
    type="http",
    params={
        "method": "GET",
        "url": "https://api.example.com/user/profile",
        "response_key": "user_profile",
    },
    transitions={"success": "next", "failure": "error"},
)
```

---

## Note on HTTP clients

`HTTPNode` creates a new `httpx.AsyncClient` per execution. For high-throughput applications, register a factory that reuses a shared client:

```python
shared_client = httpx.AsyncClient(timeout=10.0)

class PooledHTTPNode(HTTPNode):
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def _request(self, method, url, json, headers):
        return await self._client.request(method=method, url=url, json=json, headers=headers)

registry.register("http")(lambda: PooledHTTPNode(shared_client))
```
