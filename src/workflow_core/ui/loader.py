"""
ComponentLoader — renders component dicts to HTML using the bundled HTML templates.

Templates live in ``workflow_core/ui/components/*.html`` and are Jinja2 fragments.
Jinja2 compiles and caches them in memory on first use; subsequent renders have
zero disk I/O (or a single stat() per template in auto_reload=True dev mode).

Usage::

    from workflow_core.ui.loader import ComponentLoader
    from workflow_core.ui import schema as ui

    loader = ComponentLoader()          # auto_reload=True in dev
    loader = ComponentLoader(auto_reload=False)  # production

    page = ui.page([
        ui.step_progress(["Step 1", "Step 2"], active=0),
        ui.card(body=[
            ui.form(
                fields=[ui.input("email", label="Email", required=True)],
                actions=[ui.button("Submit", variant="primary")],
            )
        ]),
    ])

    html = loader.render(page, execution_id="exec-001")
    html = loader.render(page, execution_id="exec-001", errors={"email": "required"})
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2

_COMPONENTS_DIR = Path(__file__).parent / "components"

# Keys whose values are lists of child component dicts — pre-rendered before
# the parent template is rendered.
_LIST_CHILDREN: dict[str, list[tuple[str, str]]] = {
    "card":          [("header", "header_html"), ("body", "body_html")],
    "form":          [("fields", "fields_html"), ("actions", "actions_html")],
    "page":          [("components", "components_html")],
}

# Field-level component types: errors are injected by field name.
_FIELD_TYPES = {"input", "select", "textarea"}


class ComponentLoader:
    """
    Renders component dicts produced by ``workflow_core.ui.schema`` to HTML strings.

    A single loader instance is typically shared for the lifetime of the process.
    The Jinja2 environment it manages caches compiled templates in memory.
    """

    def __init__(self, auto_reload: bool = True) -> None:
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(_COMPONENTS_DIR)),
            autoescape=True,
            auto_reload=auto_reload,
        )

    def render(
        self,
        component: dict[str, Any],
        *,
        execution_id: str = "",
        errors: dict[str, str] | None = None,
    ) -> str:
        """Render a component dict (and its children) to an HTML string."""
        return self._render(component, execution_id=execution_id, errors=errors or {})

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _render(
        self,
        component: dict[str, Any],
        *,
        execution_id: str,
        errors: dict[str, str],
    ) -> str:
        comp_type: str = component.get("type", "")
        props: dict[str, Any] = {k: v for k, v in component.items() if k != "type"}

        # Pre-render list children
        for src_key, dst_key in _LIST_CHILDREN.get(comp_type, []):
            children = props.pop(src_key, [])
            props[dst_key] = "".join(
                self._render(c, execution_id=execution_id, errors=errors)
                for c in children
            )

        # Pre-render grid columns: list[list[component]] → list[(html, width)]
        if comp_type == "grid":
            raw_columns: list[list[dict[str, Any]]] = props.pop("columns", [])
            widths: list[str] = props.pop("widths", [])
            rendered_cols = []
            for i, col in enumerate(raw_columns):
                col_html = "".join(
                    self._render(c, execution_id=execution_id, errors=errors)
                    for c in col
                )
                width = widths[i] if i < len(widths) else "uk-width-expand"
                rendered_cols.append((col_html, width))
            props["columns"] = rendered_cols

        # Inject error for field-level components
        if comp_type in _FIELD_TYPES:
            props.setdefault("error", errors.get(props.get("name", ""), ""))

        # Inject error_summary flag for forms
        if comp_type == "form":
            props["error_summary"] = bool(errors)

        # Always inject execution_id
        props["execution_id"] = execution_id

        tmpl = self._env.get_template(f"{comp_type}.html")
        return tmpl.render(**props)
