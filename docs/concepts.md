# Concepts

## The core idea

Applications are execution systems. A request enters, data flows through transformations, state evolves, a response comes out. `workflow-core` makes that execution path explicit and declarative instead of hiding it across controllers, services, and ORM hooks.

---

## State machine

A `Workflow` is a state machine. Each `Node` is a state. Each node declares where execution goes next based on the outcome.

```
"collect"   ──success──▶  "verify"
            ──failure──▶  "reject"

"verify"    ──approved──▶  "create_account"
            ──rejected──▶  "reject"

"create_account"  ──success──▶  None  (end)

"reject"    ──success──▶  None  (end)
```

This is the entire execution topology, visible in one place. No hidden branching inside service methods. No conditional logic spread across files.

### Transitions

Each node has a `transitions` dict: outcome key → next node id (or `None` to end).

```python
Node(
    type="decision",
    params={"key": "kyc_status", "operator": "eq", "value": "approved"},
    transitions={
        "true":  "create_account",
        "false": "reject",
    },
)
```

The node returns `Result(transition="true")` or `Result(transition="false")`. The runtime follows the matching transition.

---

## Context

`Context` is the single object that carries all execution state from node to node.

```python
Context(
    execution_id="exec_001",
    workflow_id="onboarding",
    node="verify_kyc",          # current state
    data={"name": "Alice", ...} # accumulated data
)
```

### Context is immutable

Nodes never mutate context. They return output data. The runtime merges it in:

```python
# node returns this
Result(output={"kyc_result": {"status": "approved"}})

# runtime produces this
context.merge({"kyc_result": {"status": "approved"}})
# → new Context with data = {**old_data, "kyc_result": {...}}
```

### Context is append-only

Each node adds to `context.data`. Earlier keys are never deleted or overwritten by the runtime. By the end of the workflow, `context.data` is a complete record of everything that happened.

### Reading context in a node

```python
class MyNode:
    async def run(self, context: Context, params: dict) -> Result | NodeError:
        name = context.data.get("validated", {}).get("name")
        ...
```

Nodes read from `context.data`. They never write to it directly.

---

## Nodes

A node is a single unit of work. It receives the current context and its configuration params. It returns a `Result` or `NodeError`.

```
Context + params
    ↓
Node.run()
    ↓
Result(output={...}, transition="success")
  or
NodeError(code="...", message="...", transition="failure")
```

### Result

A successful outcome. Carries output data to merge into context, and a transition key.

```python
Result(output={"user_id": 42}, transition="success")
```

### NodeError

A failed outcome. Carries a structured error and a transition key (defaults to `"failure"`).

```python
NodeError(code="VALIDATION_ERROR", message="Age is required", details={"age": "required"})
```

`NodeError` is not an exception. It is a value. The runtime follows its `transition` key like any other outcome — a node error can route to an error-handling state, not necessarily terminate the workflow.

---

## The execution loop

```
while context.node is not None:

    node_def = workflow.nodes[context.node]     # get current state definition
    node = registry.resolve(node_def.type)()    # instantiate node class
    result = await node.run(context, params)    # run the node

    next_node = node_def.transitions[result.transition]  # follow the outcome
    context = context.merge(result.output).evolve(node=next_node)

emit WORKFLOW_COMPLETED
return context
```

The runtime drives sequencing. Nodes never call each other.

---

## Events

The runtime emits an `Event` at every execution boundary. This is the observability surface.

```
NODE_STARTED        → before node.run()
NODE_COMPLETED      → after node.run(), carries the transition key
TRANSITION_SELECTED → after transition resolved, carries next node
WORKFLOW_COMPLETED  → after the loop exits
WORKFLOW_FAILED     → if the runtime raises
```

Subscribe by passing an `on_event` callback to `runtime.execute()`:

```python
events = []

context = await runtime.execute(
    "exec_001",
    input_data={...},
    on_event=events.append,          # sync callback
)

# or async
async def log_event(event: Event) -> None:
    print(f"{event.type} | node={event.node_id}")

context = await runtime.execute("exec_001", on_event=log_event)
```

Events are immutable. They carry `execution_id`, `node_id`, `timestamp`, and a `data` dict with transition details.

---

## Registry

The `Registry` decouples node type names (used in workflow definitions) from the classes that implement them.

```python
registry = Registry()

# built-in node
registry.register("form")(FormNode)

# custom node — no args
@registry.register("send_email")
class SendEmailNode:
    async def run(self, context, params): ...

# node needing dependencies — register a factory
repo = RedisRepository(redis_client)
registry.register("persist")(lambda: PersistNode(repo))
```

The runtime calls `registry.resolve("form")()` to instantiate the node for each execution. Nodes are stateless — a new instance is created per node execution.
