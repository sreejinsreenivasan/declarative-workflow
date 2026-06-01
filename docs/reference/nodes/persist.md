# PersistNode

Reads from or writes to a storage backend via an injected `Repository`.

```python
from workflow_core.nodes import PersistNode, Repository
```

`PersistNode` requires a `Repository` dependency. Register a factory:

```python
repo = RedisRepository(redis_client)
registry.register("persist")(lambda: PersistNode(repo))
```

---

## Params

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `key` | `str` | required | Storage key to read/write/delete |
| `operation` | `str` | `"write"` | `"write"`, `"read"`, or `"delete"` |
| `data_key` | `str` | `"validated"` | `context.data` key for the data to write (write only) |
| `output_key` | `str` | `"record"` | `context.data` key for the read result (read only) |

---

## Transitions

| Key | When |
|-----|------|
| `"success"` | Operation succeeded |
| `"failure"` | Missing `key` param or unknown `operation` |
| `"failure"` | `"read"` — record not found (`NOT_FOUND`) |

---

## Operations

### write

Reads `context.data[data_key]` and stores it under `key`.

```python
# writes context.data["validated"] to storage key "user:42"
params={"operation": "write", "key": "user:42", "data_key": "validated"}
# → Result(output={"persisted": True})
```

### read

Retrieves the record at `key` and stores it in `context.data[output_key]`.

```python
params={"operation": "read", "key": "user:42", "output_key": "user"}
# → Result(output={"user": {...record...}})
# or
# → NodeError(code="NOT_FOUND", message="Record 'user:42' not found")
```

### delete

Removes the record at `key`.

```python
params={"operation": "delete", "key": "user:42"}
# → Result(output={"deleted": True})
```

---

## Repository protocol

```python
from workflow_core.nodes import Repository

class Repository(Protocol):
    async def get(self, key: str) -> dict[str, Any] | None: ...
    async def set(self, key: str, value: dict[str, Any]) -> None: ...
    async def delete(self, key: str) -> None: ...
```

Implement this protocol to use any storage backend. The built-in Redis implementation ships in `workflow_core.adapters.redis` (see Adapters).

---

## Example

```python
Node(
    type="persist",
    params={
        "operation": "write",
        "key": "user:new",
        "data_key": "validated",
    },
    transitions={"success": "respond_created", "failure": "persist_error"},
)
```
