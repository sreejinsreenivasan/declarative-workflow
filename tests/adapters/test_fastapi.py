"""
FastAPI adapter tests.

Uses httpx.AsyncClient + ASGITransport to exercise the real ASGI app
without a running server.
"""
import jinja2
import pytest
import httpx
from fastapi import FastAPI

from workflow_core import InMemoryStore, Registry, Runtime, Workflow, Node
from workflow_core.nodes import FormNode, ResponseNode
from workflow_core.nodes.ui import UINode
from workflow_core.adapters.fastapi import api_router, ui_router


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FORM_FIELDS = {
    "name": {"type": "str", "required": True},
    "age":  {"type": "int", "required": True, "min": 0},
}

TEMPLATES = {
    "form.html":  "<form action='/ui/{{ execution_id }}'>{{ node }}</form>",
    "_form.html": "<partial>{{ errors }}</partial>",
}


def make_env() -> jinja2.Environment:
    return jinja2.Environment(loader=jinja2.DictLoader(TEMPLATES))


def api_workflow() -> tuple[Workflow, Registry]:
    workflow = Workflow(
        id="create_user",
        start="collect",
        nodes={
            "collect": Node(
                type="form",
                params={"fields": FORM_FIELDS},
                transitions={"success": "respond_ok", "failure": "respond_err"},
            ),
            "respond_ok":  Node(type="response", params={"status": 201}, transitions={"success": None}),
            "respond_err": Node(type="response", params={"status": 422}, transitions={"success": None}),
        },
    )
    registry = Registry()
    registry.register("form")(FormNode)
    registry.register("response")(ResponseNode)
    return workflow, registry


def ui_workflow() -> tuple[Workflow, Registry]:
    env = make_env()
    workflow = Workflow(
        id="onboarding",
        start="step1",
        nodes={
            "step1": Node(
                type="ui",
                params={
                    "template": "form.html",
                    "partial_template": "_form.html",
                    "fields": FORM_FIELDS,
                },
                transitions={"render": None, "submitted": "done", "error": None},
            ),
            "done": Node(
                type="response",
                params={"status": 200, "include": ["validated"]},
                transitions={"success": None},
            ),
        },
    )
    registry = Registry()
    registry.register("ui")(lambda: UINode(env))
    registry.register("response")(ResponseNode)
    return workflow, registry


# ---------------------------------------------------------------------------
# api_router
# ---------------------------------------------------------------------------

@pytest.fixture
def api_app() -> FastAPI:
    workflow, registry = api_workflow()
    runtime = Runtime(workflow, registry)
    app = FastAPI()
    app.include_router(api_router(runtime))
    return app


@pytest.fixture
def api_client(api_app) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api_app),
        base_url="http://test",
    )


async def test_api_execute_valid_input(api_client):
    async with api_client as client:
        resp = await client.post("/execute", json={"name": "Alice", "age": 30})
    assert resp.status_code == 201


async def test_api_execute_returns_response_data(api_client):
    async with api_client as client:
        resp = await client.post("/execute", json={"name": "Alice", "age": 30})
    data = resp.json()
    assert "validated" in data  # response node includes all data by default


async def test_api_execute_invalid_input_returns_422(api_client):
    async with api_client as client:
        resp = await client.post("/execute", json={"name": "Alice"})  # missing age
    assert resp.status_code == 422


async def test_api_execute_with_id(api_client):
    async with api_client as client:
        resp = await client.post("/execute/exec-123", json={"name": "Alice", "age": 25})
    assert resp.status_code == 201


async def test_api_execute_with_id_is_idempotent(api_client):
    """Same execution_id can be called multiple times — each starts a fresh execution."""
    async with api_client as client:
        r1 = await client.post("/execute/e1", json={"name": "Alice", "age": 25})
        r2 = await client.post("/execute/e1", json={"name": "Alice", "age": 25})
    assert r1.status_code == 201
    assert r2.status_code == 201


async def test_api_execute_content_type_is_json(api_client):
    async with api_client as client:
        resp = await client.post("/execute", json={"name": "Alice", "age": 30})
    assert "application/json" in resp.headers["content-type"]


# ---------------------------------------------------------------------------
# ui_router
# ---------------------------------------------------------------------------

@pytest.fixture
def ui_app() -> FastAPI:
    workflow, registry = ui_workflow()
    store = InMemoryStore()
    runtime = Runtime(workflow, registry, store=store)
    app = FastAPI()
    app.include_router(ui_router(runtime, prefix="/ui"))
    return app


@pytest.fixture
def ui_client(ui_app) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=ui_app),
        base_url="http://test",
    )


async def test_ui_get_new_returns_html(ui_client):
    async with ui_client as client:
        resp = await client.get("/ui/new")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "<form" in resp.text


async def test_ui_get_new_embeds_execution_id(ui_client):
    async with ui_client as client:
        resp = await client.get("/ui/new")
    assert "action='/ui/" in resp.text


async def test_ui_get_unknown_execution_returns_404(ui_client):
    async with ui_client as client:
        resp = await client.get("/ui/nonexistent-id")
    assert resp.status_code == 404


async def test_ui_post_unknown_execution_returns_404(ui_client):
    async with ui_client as client:
        resp = await client.post("/ui/nonexistent-id", data={"name": "Alice", "age": "30"})
    assert resp.status_code == 404


async def test_ui_post_valid_form_completes_workflow(ui_client):
    async with ui_client as client:
        # Start
        get_resp = await client.get("/ui/new")
        assert get_resp.status_code == 200

        # Extract execution_id from the form action
        html = get_resp.text
        exec_id = html.split("action='/ui/")[1].split("'")[0]

        # Submit valid form
        post_resp = await client.post(f"/ui/{exec_id}", data={"name": "Alice", "age": "30"})

    # Workflow completes → response node → JSON returned
    assert post_resp.status_code == 200
    assert "application/json" in post_resp.headers["content-type"]


async def test_ui_post_invalid_form_re_renders_html(ui_client):
    async with ui_client as client:
        get_resp = await client.get("/ui/new")
        exec_id = get_resp.text.split("action='/ui/")[1].split("'")[0]

        # Submit missing age
        post_resp = await client.post(f"/ui/{exec_id}", data={"name": "Alice"})

    # Workflow suspends at same node → HTML returned with errors
    assert "text/html" in post_resp.headers["content-type"]


async def test_ui_htmx_request_uses_partial_template(ui_client):
    async with ui_client as client:
        resp = await client.get("/ui/new", headers={"HX-Request": "true"})
    assert "<partial>" in resp.text


async def test_ui_get_renders_current_node_after_suspend(ui_client):
    async with ui_client as client:
        # Start new execution
        start = await client.get("/ui/new")
        exec_id = start.text.split("action='/ui/")[1].split("'")[0]

        # GET again — should resume at same node
        resume = await client.get(f"/ui/{exec_id}")
    assert resume.status_code == 200
    assert "<form" in resume.text
