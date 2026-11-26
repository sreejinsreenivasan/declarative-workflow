import json

import pytest

from workflow_core import ExecutionStatus, Runtime
from workflow_core.adapters.file_store import FileStore
from workflow_core.context import Context
from workflow_core.registry import Registry
from workflow_core.result import Result
from workflow_core.workflow import Node, Workflow


def ctx(eid: str = "e1", **kw) -> Context:
    return Context(execution_id=eid, workflow_id="w", node="a", data={"k": "v"}, **kw)


async def test_save_and_load_round_trip(tmp_path):
    store = FileStore(tmp_path / "runs")
    await store.save("e1", ctx(status=ExecutionStatus.SUSPENDED))
    loaded = await store.load("e1")
    assert loaded == ctx(status=ExecutionStatus.SUSPENDED)


async def test_load_missing_returns_none(tmp_path):
    assert await FileStore(tmp_path).load("nope") is None


async def test_file_is_readable_json(tmp_path):
    store = FileStore(tmp_path)
    await store.save("e1", ctx())
    data = json.loads((tmp_path / "e1.json").read_text())
    assert data["execution_id"] == "e1" and data["status"] == "running"


async def test_save_overwrites_and_leaves_no_temp_files(tmp_path):
    store = FileStore(tmp_path)
    await store.save("e1", ctx())
    await store.save("e1", ctx(status=ExecutionStatus.COMPLETED))
    assert (await store.load("e1")).status == ExecutionStatus.COMPLETED
    assert sorted(p.name for p in tmp_path.iterdir()) == ["e1.json"]


@pytest.mark.parametrize("bad", ["../escape", "a/b", "", ".hidden", "x\\y"])
async def test_unsafe_execution_ids_are_rejected(tmp_path, bad):
    store = FileStore(tmp_path)
    with pytest.raises(ValueError, match="execution id"):
        await store.save(bad, ctx())
    with pytest.raises(ValueError, match="execution id"):
        await store.load(bad)


async def test_works_as_runtime_store_across_instances(tmp_path):
    def gate():
        class _N:
            async def run(self, context, params):
                return Result(transition="approved" if context.data.get("ok") else "waiting")

        return _N

    wf = Workflow(
        id="w",
        start="g",
        nodes={"g": Node(type="g", transitions={"waiting": None, "approved": None})},
    )
    reg = Registry()
    reg.register("g")(gate())
    first = Runtime(wf, reg, store=FileStore(tmp_path), suspend_on=frozenset({"waiting"}))
    await first.execute("run-1")
    second = Runtime(
        wf, reg, store=FileStore(tmp_path), suspend_on=frozenset({"waiting"})
    )  # e.g. after a restart
    done = await second.resume("run-1", {"ok": True})
    assert done.status == ExecutionStatus.COMPLETED
