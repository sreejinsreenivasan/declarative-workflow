from __future__ import annotations

from uuid import uuid4

try:
    from fastapi import APIRouter, Request
    from fastapi.responses import HTMLResponse, JSONResponse, Response
except ImportError as exc:
    raise ImportError(
        "FastAPI is required for this adapter. "
        "Install it with: pip install 'workflow-core[fastapi]'"
    ) from exc

from workflow_core.context import Context
from workflow_core.runtime import Runtime


def api_router(runtime: Runtime, prefix: str = "") -> APIRouter:
    """
    Mount a workflow as a JSON API.

    Routes
    ------
    POST /execute            start execution, auto-generate execution_id
    POST /execute/{id}       start execution with a specific execution_id
    """
    router = APIRouter(prefix=prefix)

    @router.post("/execute")
    async def execute(request: Request) -> Response:
        body = await request.json()
        context = await runtime.execute(str(uuid4()), input_data={"input": body})
        return _json_response(context)

    @router.post("/execute/{execution_id}")
    async def execute_with_id(execution_id: str, request: Request) -> Response:
        body = await request.json()
        context = await runtime.execute(execution_id, input_data={"input": body})
        return _json_response(context)

    return router


def ui_router(runtime: Runtime, prefix: str = "") -> APIRouter:
    """
    Mount a workflow as an HTMX / server-side-rendered UI.

    Routes
    ------
    GET  /new               start a fresh execution, return first form
    GET  /{execution_id}    resume and render current step
    POST /{execution_id}    submit form data, return next step or final response
    """
    router = APIRouter(prefix=prefix)

    @router.get("/new")
    async def start(request: Request) -> HTMLResponse:
        execution_id = str(uuid4())
        context = await runtime.execute(
            execution_id,
            input_data=_request_meta(request, "GET"),
        )
        return HTMLResponse(content=context.data.get("html", ""))

    @router.get("/{execution_id}")
    async def render(execution_id: str, request: Request) -> Response:
        try:
            context = await runtime.resume(
                execution_id,
                input_data=_request_meta(request, "GET"),
            )
        except RuntimeError:
            return JSONResponse(
                content={"error": f"Execution '{execution_id}' not found"},
                status_code=404,
            )
        return _html_or_json(context)

    @router.post("/{execution_id}")
    async def submit(execution_id: str, request: Request) -> Response:
        form = dict(await request.form())
        try:
            context = await runtime.resume(
                execution_id,
                input_data={**_request_meta(request, "POST"), "input": form},
            )
        except (RuntimeError, KeyError) as e:
            return JSONResponse(
                content={"error": f"Execution '{execution_id}' not found", "detail": str(e)},
                status_code=404,
            )
        return _html_or_json(context)

    return router


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _json_response(context: Context) -> JSONResponse:
    r = context.data.get("response", {})
    return JSONResponse(content=r.get("data", {}), status_code=r.get("status", 200))


def _html_or_json(context: Context) -> Response:
    """Return HTML if workflow is suspended, JSON if completed."""
    if "response" in context.data:
        return _json_response(context)
    return HTMLResponse(content=context.data.get("html", ""))


def _request_meta(request: Request, method: str) -> dict[str, dict[str, str | bool]]:
    return {
        "request": {
            "method": method,
            "is_htmx": "HX-Request" in request.headers,
        }
    }
