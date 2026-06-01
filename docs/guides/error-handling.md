# Error Handling

## NodeError is a value, not an exception

`NodeError` is a normal return value — not a raised exception. The runtime treats it the same as `Result`: it reads the `transition` key and follows it.

```python
# both of these are handled identically by the runtime
return Result(transition="success")
return NodeError(code="VALIDATION_ERROR", message="...", transition="failure")
```

This means errors route through the state machine like any other outcome.

---

## Routing errors to recovery states

Define explicit error states in your workflow:

```python
nodes={
    "verify_kyc": Node(
        type="http",
        params={"method": "POST", "url": "https://kyc.example.com"},
        transitions={
            "success": "create_account",
            "failure": "kyc_failed",        # HTTP error routes here
        },
    ),
    "create_account": Node(
        type="persist",
        transitions={"success": "respond_ok", "failure": "persist_failed"},
    ),
    "respond_ok": Node(
        type="response",
        params={"status": 201},
        transitions={"success": None},
    ),
    "kyc_failed": Node(
        type="response",
        params={"status": 422, "include": []},
        transitions={"success": None},
    ),
    "persist_failed": Node(
        type="response",
        params={"status": 500},
        transitions={"success": None},
    ),
}
```

Every failure has a named state. No silent swallowing, no mystery 500s.

---

## Custom error transitions

A node can return any transition key, not just `"failure"`. Use this to route different error types to different states:

```python
class PaymentNode:
    async def run(self, context, params):
        result = await charge(context.data["card"])

        if result.declined:
            return NodeError(
                code="PAYMENT_DECLINED",
                message="Card declined",
                transition="declined",
            )

        if result.network_error:
            return NodeError(
                code="NETWORK_ERROR",
                message="Payment gateway unreachable",
                transition="retry",
            )

        return Result(output={"transaction_id": result.id})
```

Workflow definition:

```python
Node(
    type="payment",
    transitions={
        "success":  "confirm",
        "declined": "prompt_new_card",
        "retry":    "retry_payment",
        "failure":  "payment_error",
    },
)
```

---

## Unexpected exceptions

If a node raises an unhandled exception, the runtime wraps it in a `NodeError` and uses the `"failure"` transition:

```python
NodeError(code="UNEXPECTED_ERROR", message=str(exc))
```

This means your workflow must declare a `"failure"` transition on any node that might raise, or the runtime will raise a `RuntimeError` about an unknown transition.

**Best practice:** always handle expected errors explicitly inside the node and return `NodeError`. Let unhandled exceptions be truly unexpected — they indicate bugs, not business logic.

---

## Detecting errors in the final context

After execution, inspect `context.data` to determine the outcome:

```python
context = await runtime.execute("exec_001", input_data={...})

response = context.data.get("response", {})
status = response.get("status", 200)

if status >= 400:
    # something failed — check what state we ended in
    print(f"Workflow ended at node: {context.node}")
```

Alternatively, use the `on_event` callback to track `NODE_COMPLETED` events and inspect their `transition` data.

---

## Unknown transitions

If a node returns a transition key that is not declared in the node's `transitions` dict, the runtime raises immediately:

```python
RuntimeError: node 'verify_kyc': unknown transition 'approved'
```

This is a configuration error — fix the workflow definition to declare the missing transition. The runtime never silently skips an undeclared transition.
