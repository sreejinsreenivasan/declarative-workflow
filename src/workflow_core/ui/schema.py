"""
Component schema helpers — thin dict factories for building page schemas.

Import as a namespace to avoid shadowing Python builtins::

    from workflow_core.ui import schema as ui

    page = ui.page([
        ui.step_progress(["1 · Info", "2 · Nodes", "3 · Review"], active=0),
        ui.card(body=[
            ui.form(
                fields=[
                    ui.input("workflow_id", label="Workflow ID", required=True),
                ],
                actions=[ui.button("Continue →", variant="primary")],
            )
        ]),
    ])
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Form inputs
# ---------------------------------------------------------------------------

def input(  # noqa: A001
    name: str,
    *,
    label: str = "",
    input_type: str = "text",
    placeholder: str = "",
    required: bool = False,
    hint: str = "",
) -> dict[str, Any]:
    return {
        "type": "input",
        "name": name,
        "label": label,
        "input_type": input_type,
        "placeholder": placeholder,
        "required": required,
        "hint": hint,
    }


def select(
    name: str,
    *,
    label: str = "",
    options: list[tuple[str, str]] | None = None,
    required: bool = False,
) -> dict[str, Any]:
    return {
        "type": "select",
        "name": name,
        "label": label,
        "options": options or [],
        "required": required,
    }


def textarea(
    name: str,
    *,
    label: str = "",
    placeholder: str = "",
    rows: int = 4,
    hint: str = "",
    monospace: bool = False,
) -> dict[str, Any]:
    return {
        "type": "textarea",
        "name": name,
        "label": label,
        "placeholder": placeholder,
        "rows": rows,
        "hint": hint,
        "monospace": monospace,
    }


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def button(
    text: str,
    *,
    variant: str = "default",
    name: str = "",
    value: str = "",
    button_type: str = "submit",
    icon: str = "",
    size: str = "",
) -> dict[str, Any]:
    """
    Variants: default, primary, secondary, destructive (or danger), ghost, text, link.
    Sizes: xs, sm, md, lg (maps to uk-btn-{size}).
    """
    return {
        "type": "button",
        "text": text,
        "variant": variant,
        "name": name,
        "value": value,
        "button_type": button_type,
        "icon": icon,
        "size": size,
    }


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

def alert(message: str, *, variant: str = "danger") -> dict[str, Any]:
    return {"type": "alert", "message": message, "variant": variant}


def badge(text: str, *, active: bool = False) -> dict[str, Any]:
    return {"type": "badge", "text": text, "active": active}


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

def divider() -> dict[str, Any]:
    return {"type": "divider"}


def card(
    *,
    header: list[dict[str, Any]] | None = None,
    body: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {"type": "card", "header": header or [], "body": body or []}


def form(
    *,
    fields: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
    hx_target: str = "#content",
    hx_swap: str = "innerHTML",
    indicator_id: str = "spinner",
) -> dict[str, Any]:
    return {
        "type": "form",
        "fields": fields or [],
        "actions": actions or [],
        "hx_target": hx_target,
        "hx_swap": hx_swap,
        "indicator_id": indicator_id,
    }


def grid(
    columns: list[list[dict[str, Any]]],
    *,
    widths: list[str] | None = None,
) -> dict[str, Any]:
    return {"type": "grid", "columns": columns, "widths": widths or []}


# ---------------------------------------------------------------------------
# Composite
# ---------------------------------------------------------------------------

def step_progress(steps: list[str], *, active: int = 0) -> dict[str, Any]:
    return {"type": "step_progress", "steps": steps, "active": active}


def code_block(
    content: str,
    *,
    element_id: str = "",
    max_height: str = "28rem",
) -> dict[str, Any]:
    return {
        "type": "code_block",
        "content": content,
        "element_id": element_id,
        "max_height": max_height,
    }


def node_list(nodes: dict[str, Any], *, start: str | None = None) -> dict[str, Any]:
    return {"type": "node_list", "nodes": nodes, "start": start}


def text(content: str, *, variant: str = "small") -> dict[str, Any]:
    return {"type": "text", "content": content, "variant": variant}


def raw(html: str) -> dict[str, Any]:
    return {"type": "raw", "html": html}


# ---------------------------------------------------------------------------
# Page root
# ---------------------------------------------------------------------------

def page(components: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "page", "components": components}
