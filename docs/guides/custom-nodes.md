# Custom Nodes

Any class with an `async def run(self, context, params)` method satisfies `NodeProtocol` and can be registered as a node type.

---

## Minimal custom node

```python
from workflow_core import Context
from workflow_core.result import Result, NodeError


class SendEmailNode:
    async def run(self, context: Context, params: dict) -> Result | NodeError:
        recipient = context.data.get("validated", {}).get("email")
        template  = params.get("template", "welcome")

        if not recipient:
            return NodeError(code="MISSING_EMAIL", message="No email in context")

        # your email sending logic here
        await send_email(recipient, template)

        return Result(output={"email_sent": True})
```

Register it:

```python
from workflow_core import Registry

registry = Registry()

@registry.register("send_email")
class SendEmailNode:
    async def run(self, context, params): ...
```

Use it in a workflow:

```python
Node(
    type="send_email",
    params={"template": "welcome"},
    transitions={"success": "respond", "failure": "respond"},
)
```

---

## Nodes with dependencies

Nodes that need infrastructure (database clients, HTTP clients, queues) take their dependencies in `__init__`. Register a factory so the dependency is injected at construction time:

```python
class NotifyNode:
    def __init__(self, slack_client: SlackClient) -> None:
        self._slack = slack_client

    async def run(self, context: Context, params: dict) -> Result | NodeError:
        channel = params.get("channel", "#alerts")
        message = context.data.get("summary", "")
        await self._slack.post(channel, message)
        return Result()


# wire up the dependency
slack = SlackClient(token=os.environ["SLACK_TOKEN"])
registry.register("notify")(lambda: NotifyNode(slack))
```

---

## Rules every node must follow

**Must:**

- Be `async def run(self, context, params) -> Result | NodeError`
- Return `Result` or `NodeError` — never raise unhandled exceptions
- Be stateless — no mutable instance state that persists between executions
- Log execution start and completion if running in production

**Must not:**

- Call another node directly — the runtime drives sequencing
- Write to `context.data` directly — return output in `Result.output`
- Import from `workflow_core.adapters` — nodes are framework-agnostic
- Block the event loop — all I/O must be `await`ed

---

## Returning errors

Always return `NodeError`, never raise:

```python
# correct
if not value:
    return NodeError(code="MISSING_VALUE", message="value is required")

# wrong — unhandled exceptions are caught by the runtime but lose context
if not value:
    raise ValueError("value is required")
```

Custom transition on error:

```python
return NodeError(
    code="PAYMENT_DECLINED",
    message="Card declined",
    details={"reason": "insufficient_funds"},
    transition="declined",   # routes to "declined" state instead of "failure"
)
```

The workflow must declare this transition:

```python
Node(
    type="charge_card",
    transitions={
        "success":  "confirm_order",
        "declined": "prompt_retry",
        "failure":  "payment_error",
    },
)
```

---

## Reading params and context

```python
async def run(self, context: Context, params: dict) -> Result | NodeError:
    # from params (static config in workflow definition)
    url     = params.get("url")
    timeout = params.get("timeout", 30)

    # from context (accumulated execution data)
    user_id  = context.data.get("validated", {}).get("user_id")
    kyc_data = context.data.get("kyc_result", {})
```

---

## Producing output

Output from `Result` is merged into `context.data` by the runtime. Use descriptive keys:

```python
return Result(
    output={
        "payment_result": {
            "transaction_id": "txn_abc123",
            "amount":         99.99,
            "currency":       "USD",
        }
    },
    transition="success",
)
```

The next node can then read `context.data["payment_result"]`.
