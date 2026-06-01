from typing import Any
from unittest.mock import AsyncMock

import pytest

from workflow_core.context import Context
from workflow_core.nodes.persist import PersistNode
from workflow_core.result import NodeError, Result


def ctx(data: dict) -> Context:
    return Context(execution_id="e1", workflow_id="w1", node="persist", data=data)


def make_repo(record: dict | None = None) -> AsyncMock:
    repo = AsyncMock()
    repo.get = AsyncMock(return_value=record)
    repo.set = AsyncMock()
    repo.delete = AsyncMock()
    return repo


async def test_write_persists_data():
    repo = make_repo()
    result = await PersistNode(repo).run(
        ctx({"validated": {"name": "Alice", "age": 30}}),
        {"operation": "write", "key": "user:1"},
    )
    repo.set.assert_awaited_once_with("user:1", {"name": "Alice", "age": 30})
    assert isinstance(result, Result)
    assert result.output["persisted"] is True


async def test_write_uses_custom_data_key():
    repo = make_repo()
    await PersistNode(repo).run(
        ctx({"payload": {"email": "a@b.com"}}),
        {"operation": "write", "key": "user:2", "data_key": "payload"},
    )
    repo.set.assert_awaited_once_with("user:2", {"email": "a@b.com"})


async def test_read_returns_record():
    repo = make_repo(record={"name": "Alice"})
    result = await PersistNode(repo).run(
        ctx({}),
        {"operation": "read", "key": "user:1"},
    )
    assert isinstance(result, Result)
    assert result.output["record"] == {"name": "Alice"}


async def test_read_with_custom_output_key():
    repo = make_repo(record={"name": "Alice"})
    result = await PersistNode(repo).run(
        ctx({}),
        {"operation": "read", "key": "user:1", "output_key": "user"},
    )
    assert "user" in result.output


async def test_read_not_found_returns_error():
    repo = make_repo(record=None)
    result = await PersistNode(repo).run(ctx({}), {"operation": "read", "key": "user:99"})
    assert isinstance(result, NodeError)
    assert result.code == "NOT_FOUND"


async def test_delete_removes_record():
    repo = make_repo()
    result = await PersistNode(repo).run(ctx({}), {"operation": "delete", "key": "user:1"})
    repo.delete.assert_awaited_once_with("user:1")
    assert result.output["deleted"] is True


async def test_missing_key_returns_error():
    repo = make_repo()
    result = await PersistNode(repo).run(ctx({}), {"operation": "write"})
    assert isinstance(result, NodeError)
    assert result.code == "INVALID_PARAMS"


async def test_unknown_operation_returns_error():
    repo = make_repo()
    result = await PersistNode(repo).run(ctx({}), {"operation": "upsert", "key": "x"})
    assert isinstance(result, NodeError)
    assert result.code == "INVALID_OPERATION"


async def test_default_operation_is_write():
    repo = make_repo()
    result = await PersistNode(repo).run(
        ctx({"validated": {"x": 1}}),
        {"key": "k"},
    )
    repo.set.assert_awaited_once()
    assert isinstance(result, Result)
