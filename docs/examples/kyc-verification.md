# Example: KYC Verification

Collects identity fields, calls an external KYC provider, evaluates the result, and routes to an approved or rejected response.

---

## Flow

```
collect_identity  ──success──▶  call_kyc_provider
                  ──failure──▶  respond_invalid

call_kyc_provider ──success──▶  check_kyc_status
                  ──failure──▶  respond_provider_error

check_kyc_status  ──true───▶  respond_approved
                  ──false──▶  respond_rejected

respond_*         ──success──▶  None
```

---

## Code

```python
import asyncio
from workflow_core import Workflow, Node, Runtime, Registry
from workflow_core.nodes import FormNode, HTTPNode, DecisionNode, TransformNode, ResponseNode


def build_registry() -> Registry:
    registry = Registry()
    registry.register("form")(FormNode)
    registry.register("http")(HTTPNode)
    registry.register("decision")(DecisionNode)
    registry.register("transform")(TransformNode)
    registry.register("response")(ResponseNode)
    return registry


workflow = Workflow(
    id="kyc_verification",
    start="collect_identity",
    nodes={
        "collect_identity": Node(
            type="form",
            params={
                "fields": {
                    "full_name":    {"type": "str", "required": True},
                    "date_of_birth": {"type": "str", "required": True},
                    "id_number":    {"type": "str", "required": True},
                }
            },
            transitions={
                "success": "call_kyc_provider",
                "failure": "respond_invalid",
            },
        ),

        "call_kyc_provider": Node(
            type="http",
            params={
                "method":       "POST",
                "url":          "https://kyc.example.com/verify",
                "body_key":     "validated",
                "response_key": "kyc_result",
                "headers":      {"X-API-Key": "secret"},
            },
            transitions={
                "success": "check_kyc_status",
                "failure": "respond_provider_error",
            },
        ),

        "check_kyc_status": Node(
            type="decision",
            params={
                "key":      "kyc_result.status",
                "operator": "eq",
                "value":    "approved",
            },
            transitions={
                "true":  "respond_approved",
                "false": "respond_rejected",
            },
        ),

        "respond_approved": Node(
            type="response",
            params={"status": 200, "include": ["validated", "kyc_result"]},
            transitions={"success": None},
        ),
        "respond_rejected": Node(
            type="response",
            params={"status": 422, "include": ["kyc_result"]},
            transitions={"success": None},
        ),
        "respond_invalid": Node(
            type="response",
            params={"status": 400},
            transitions={"success": None},
        ),
        "respond_provider_error": Node(
            type="response",
            params={"status": 502},
            transitions={"success": None},
        ),
    },
)


async def main():
    from unittest.mock import AsyncMock, MagicMock, patch

    registry = build_registry()
    runtime = Runtime(workflow, registry)

    # mock the KYC provider response
    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "approved", "score": 95}

    with patch("workflow_core.nodes.http.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        context = await runtime.execute(
            execution_id="exec_001",
            input_data={
                "input": {
                    "full_name":     "Alice Smith",
                    "date_of_birth": "1990-05-15",
                    "id_number":     "ID123456",
                }
            },
        )

    print(context.data["response"])
    # {
    #   "data": {
    #     "validated":  {"full_name": "Alice Smith", ...},
    #     "kyc_result": {"status": "approved", "score": 95},
    #   },
    #   "status": 200
    # }


asyncio.run(main())
```

---

## What happens step by step

| Step | Node | Action |
|------|------|--------|
| 1 | `collect_identity` | Validates full_name, date_of_birth, id_number |
| 2 | `call_kyc_provider` | POSTs `validated` to KYC API, stores response as `kyc_result` |
| 3 | `check_kyc_status` | Reads `kyc_result.status`, compares to `"approved"` |
| 4 | `respond_approved` | Returns 200 with validated fields and KYC result |

---

## Note on dot-path in DecisionNode

`DecisionNode` reads from `context.data` using simple key lookup — not dot-path resolution. To check a nested value like `kyc_result.status`, use `TransformNode` first to flatten it:

```python
"flatten_kyc": Node(
    type="transform",
    params={"mapping": {"kyc_status": "kyc_result.status"}},
    transitions={"success": "check_kyc_status"},
),

"check_kyc_status": Node(
    type="decision",
    params={"key": "kyc_status", "operator": "eq", "value": "approved"},
    ...
),
```
