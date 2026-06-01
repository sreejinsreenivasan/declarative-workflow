# Registry

```python
from workflow_core import Registry
```

Maps node type strings to node classes (or factories). The runtime uses it to resolve and instantiate nodes during execution.

---

## Constructor

```python
registry = Registry()
```

Each `Registry` instance maintains its own isolated mapping. Create one per application.

---

## register()

```python
def register(type_name: str) -> Callable[[type], type]
```

Decorator that registers a node class under a type name.

```python
@registry.register("form")
class FormNode:
    async def run(self, context, params): ...
```

Can also be used as a regular call:

```python
registry.register("form")(FormNode)
```

Raises `ValueError` if `type_name` is already registered.

---

## Registering factories

Any callable that returns a node instance can be registered. Use this to inject dependencies:

```python
# inject a Redis repository into PersistNode
repo = RedisRepository(redis_client)
registry.register("persist")(lambda: PersistNode(repo))

# inject an HTTP client into a custom node
http_client = httpx.AsyncClient(timeout=10.0)
registry.register("notify")(lambda: NotifyNode(http_client))
```

---

## resolve()

```python
def resolve(type_name: str) -> type
```

Returns the registered callable for a type name. Raises `KeyError` if not registered.

The runtime calls `registry.resolve(node_def.type)()` to instantiate the node for each execution.

---

## `in` operator

```python
"form" in registry    # True if registered
"missing" in registry # False
```

---

## Example

```python
from workflow_core import Registry
from workflow_core.nodes import FormNode, DecisionNode, HTTPNode, ResponseNode
from workflow_core.nodes import PersistNode

# built-in nodes
registry = Registry()
registry.register("form")(FormNode)
registry.register("decision")(DecisionNode)
registry.register("http")(HTTPNode)
registry.register("response")(ResponseNode)

# persist node with injected repository
repo = RedisRepository(redis_client)
registry.register("persist")(lambda: PersistNode(repo))

# custom node
@registry.register("send_email")
class SendEmailNode:
    async def run(self, context, params):
        ...
```
