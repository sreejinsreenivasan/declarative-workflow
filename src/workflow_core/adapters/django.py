from __future__ import annotations

from uuid import uuid4

try:
    from django.http import JsonResponse, HttpResponse, HttpRequest
    from django.views.decorators.http import require_http_methods
    from django.views.decorators.csrf import csrf_exempt
except ImportError:
    JsonResponse = None
    HttpResponse = None
    HttpRequest = None
    require_http_methods = None
    csrf_exempt = None

from workflow_core.context import Context
from workflow_core.runtime import Runtime


def json_api_view(runtime: Runtime):
    """
    Decorator for Django views that execute workflows as JSON APIs.

    Usage:
        @json_api_view(runtime)
        def create_user(request):
            return {"input": request.POST}

    GET /path?execution_id=xyz      resume and render
    POST /path                       start new execution
    POST /path?execution_id=xyz      start with specific id
    """
    if JsonResponse is None:
        raise ImportError(
            "Django is required for this adapter. "
            "Install it with: pip install 'workflow-core[django]'"
        )

    @csrf_exempt
    @require_http_methods(["GET", "POST"])
    async def view(request: HttpRequest):
        if request.method == "GET":
            execution_id = request.GET.get("execution_id")
            if not execution_id:
                return JsonResponse(
                    {"error": "execution_id required for GET"},
                    status=400,
                )
            try:
                context = await runtime.resume(execution_id)
            except RuntimeError:
                return JsonResponse(
                    {"error": f"Execution '{execution_id}' not found"},
                    status=404,
                )
            return _json_response(context)

        # POST
        execution_id = request.POST.get("execution_id") or str(uuid4())
        input_data = {k: v for k, v in request.POST.items() if k != "execution_id"}
        context = await runtime.execute(execution_id, input_data={"input": input_data})
        return _json_response(context)

    return view


def form_view(runtime: Runtime):
    """
    Decorator for Django views that render workflows as HTML forms.

    Supports GET (render) and POST (submit) for multi-step workflows.

    Usage:
        @form_view(runtime)
        def signup(request):
            return {}  # initial data or empty

    GET /path                       start new execution
    GET /path?execution_id=xyz      resume execution
    POST /path?execution_id=xyz     submit form data
    """
    if HttpResponse is None:
        raise ImportError(
            "Django is required for this adapter. "
            "Install it with: pip install 'workflow-core[django]'"
        )

    @csrf_exempt
    @require_http_methods(["GET", "POST"])
    async def view(request: HttpRequest):
        if request.method == "GET":
            execution_id = request.GET.get("execution_id")
            if execution_id:
                # Resume
                try:
                    context = await runtime.resume(
                        execution_id,
                        input_data=_request_meta(request),
                    )
                except RuntimeError:
                    return JsonResponse(
                        {"error": f"Execution '{execution_id}' not found"},
                        status=404,
                    )
            else:
                # Start fresh
                execution_id = str(uuid4())
                context = await runtime.execute(
                    execution_id,
                    input_data=_request_meta(request),
                )
            return _html_or_json(context)

        # POST
        execution_id = request.POST.get("execution_id")
        if not execution_id:
            return JsonResponse(
                {"error": "execution_id required for POST"},
                status=400,
            )

        form_data = {k: v for k, v in request.POST.items() if k != "execution_id"}
        try:
            context = await runtime.resume(
                execution_id,
                input_data={
                    **_request_meta(request, method="POST"),
                    "input": form_data,
                },
            )
        except RuntimeError:
            return JsonResponse(
                {"error": f"Execution '{execution_id}' not found"},
                status=404,
            )

        return _html_or_json(context)

    return view


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _json_response(context: Context):
    """Convert workflow context to JSON response."""
    r = context.data.get("response", {})
    return JsonResponse(r.get("data", {}), status=r.get("status", 200))


def _html_or_json(context: Context):
    """Return HTML if suspended, JSON if completed."""
    if "response" in context.data:
        return _json_response(context)
    html = context.data.get("html", "")
    return HttpResponse(content=html, content_type="text/html")


def _request_meta(request: HttpRequest, method: str | None = None) -> dict:
    """Extract request metadata for context."""
    if method is None:
        method = request.method
    return {
        "request": {
            "method": method,
            "is_htmx": request.headers.get("HX-Request") == "true",
        }
    }


def add_execution_id_to_form(html: str, execution_id: str) -> str:
    """
    Inject execution_id into form HTML.

    Replaces <!-- execution_id --> with hidden input field.
    """
    hidden = f'<input type="hidden" name="execution_id" value="{execution_id}">'
    return html.replace("<!-- execution_id -->", hidden)
