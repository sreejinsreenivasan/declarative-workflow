import pytest

from workflow_core.context import Context
from workflow_core.nodes.decision import DecisionNode
from workflow_core.result import NodeError, Result


def ctx(data: dict) -> Context:
    return Context(execution_id="e1", workflow_id="w1", node="decision", data=data)


async def test_eq_match_returns_true():
    result = await DecisionNode().run(
        ctx({"status": "approved"}),
        {"key": "status", "operator": "eq", "value": "approved"},
    )
    assert isinstance(result, Result)
    assert result.transition == "true"


async def test_eq_no_match_returns_false():
    result = await DecisionNode().run(
        ctx({"status": "pending"}),
        {"key": "status", "operator": "eq", "value": "approved"},
    )
    assert result.transition == "false"


async def test_neq_operator():
    result = await DecisionNode().run(
        ctx({"status": "pending"}),
        {"key": "status", "operator": "neq", "value": "approved"},
    )
    assert result.transition == "true"


async def test_gt_operator():
    result = await DecisionNode().run(ctx({"age": 18}), {"key": "age", "operator": "gt", "value": 17})
    assert result.transition == "true"


async def test_gte_operator():
    result = await DecisionNode().run(ctx({"age": 18}), {"key": "age", "operator": "gte", "value": 18})
    assert result.transition == "true"


async def test_lt_operator():
    result = await DecisionNode().run(ctx({"age": 17}), {"key": "age", "operator": "lt", "value": 18})
    assert result.transition == "true"


async def test_lte_operator():
    result = await DecisionNode().run(ctx({"age": 18}), {"key": "age", "operator": "lte", "value": 18})
    assert result.transition == "true"


async def test_in_operator():
    result = await DecisionNode().run(
        ctx({"role": "admin"}),
        {"key": "role", "operator": "in", "value": ["admin", "superuser"]},
    )
    assert result.transition == "true"


async def test_not_in_operator():
    result = await DecisionNode().run(
        ctx({"role": "user"}),
        {"key": "role", "operator": "not_in", "value": ["admin", "superuser"]},
    )
    assert result.transition == "true"


async def test_exists_operator():
    result = await DecisionNode().run(ctx({"user": "Alice"}), {"key": "user", "operator": "exists"})
    assert result.transition == "true"


async def test_not_exists_operator():
    result = await DecisionNode().run(ctx({}), {"key": "user", "operator": "not_exists"})
    assert result.transition == "true"


async def test_missing_key_param_returns_error():
    result = await DecisionNode().run(ctx({}), {"operator": "eq", "value": "x"})
    assert isinstance(result, NodeError)
    assert result.code == "INVALID_PARAMS"


async def test_unknown_operator_returns_error():
    result = await DecisionNode().run(
        ctx({"x": 1}), {"key": "x", "operator": "regex", "value": ".*"}
    )
    assert isinstance(result, NodeError)
    assert result.code == "INVALID_OPERATOR"


async def test_default_operator_is_eq():
    result = await DecisionNode().run(ctx({"x": 42}), {"key": "x", "value": 42})
    assert result.transition == "true"
