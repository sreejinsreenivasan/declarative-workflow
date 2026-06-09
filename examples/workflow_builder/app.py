"""
Workflow Builder — FastAPI application.

Run:
    poetry run uvicorn examples.workflow_builder.app:app --reload

Then open http://localhost:8000/new
"""
from __future__ import annotations

from pathlib import Path

import jinja2
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from workflow_core import InMemoryStore, Runtime
from workflow_core.adapters.fastapi import ui_router

from examples.workflow_builder.builder import BUILDER_WORKFLOW, create_registry

TEMPLATES_DIR = Path(__file__).parent / "templates"

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
)

registry = create_registry(env)
store = InMemoryStore()
runtime = Runtime(workflow=BUILDER_WORKFLOW, registry=registry, store=store)

app = FastAPI(title="Workflow Builder")
app.include_router(ui_router(runtime, prefix=""))
