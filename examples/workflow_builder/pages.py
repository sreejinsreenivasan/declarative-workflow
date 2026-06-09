"""
Workflow Builder — page schemas.

Each function returns a page component dict for a builder step.
Signature: (execution_id: str, data: dict, errors: dict) -> dict
"""
from __future__ import annotations

import json
from typing import Any

from workflow_core.ui import schema as ui

_NODE_TYPE_OPTIONS: list[tuple[str, str]] = [
    ("",          "Select a type…"),
    ("form",      "form — validate user input"),
    ("decision",  "decision — branch on a condition"),
    ("http",      "http — call an external API"),
    ("transform", "transform — map / reshape fields"),
    ("persist",   "persist — read or write storage"),
    ("response",  "response — shape final output"),
    ("ui",        "ui — server-rendered HTMX form"),
]


def workflow_meta_page(
    execution_id: str,
    data: dict[str, Any],
    errors: dict[str, str],
) -> dict[str, Any]:
    return ui.page([
        ui.step_progress(["1 · Workflow Info", "2 · Add Nodes", "3 · Review"], active=0),
        ui.card(
            header=[ui.text(
                "Give your workflow a unique identifier. "
                "Use lowercase letters, numbers, and underscores.",
                variant="muted",
            )],
            body=[ui.form(
                fields=[
                    ui.input("workflow_id", label="Workflow ID",
                             placeholder="e.g. user_onboarding", required=True),
                ],
                actions=[ui.button("Continue →", variant="primary")],
            )],
        ),
    ])


def add_node_page(
    execution_id: str,
    data: dict[str, Any],
    errors: dict[str, str],
) -> dict[str, Any]:
    builder = data.get("builder", {})
    nodes: dict[str, Any] = builder.get("nodes", {})
    node_count = len(nodes)

    form_card = ui.card(
        header=[ui.text(
            f"Node {node_count + 1}"
            + (" · will be set as start" if node_count == 0 else ""),
            variant="muted",
        )],
        body=[ui.form(
            fields=[
                ui.input("node_id", label="Node ID",
                         placeholder="e.g. validate_input", required=True),
                ui.select("node_type", label="Node Type",
                          options=_NODE_TYPE_OPTIONS, required=True),
                ui.textarea("params_json", label="Params · JSON, optional",
                            placeholder='{\n  "fields": { "email": { "type": "str", "required": true } }\n}',
                            rows=4, monospace=True),
                ui.textarea("transitions_json", label="Transitions · JSON, optional",
                            placeholder='{ "success": "next_node_id", "failure": null }',
                            rows=3, monospace=True),
            ],
            actions=[
                ui.button("+ Add Another Node", name="_action", value="add_more"),
                ui.button("Review Workflow →", name="_action", value="done", variant="primary"),
            ],
        )],
    )

    sidebar = ui.card(
        header=[ui.badge(f"{node_count} node{'s' if node_count != 1 else ''} added")],
        body=[ui.node_list(nodes=nodes, start=builder.get("start"))],
    )

    return ui.page([
        ui.step_progress(["1 · Done", "2 · Add Nodes", "3 · Review"], active=1),
        ui.raw(
            f'<h1 class="uk-heading-small uk-margin-small-bottom">'
            f'Add a node'
            f'<span class="uk-text-muted"> / {builder.get("id", "")}</span>'
            f'</h1>'
        ),
        ui.grid([[form_card], [sidebar]], widths=["uk-width-2-3@m", "uk-width-1-3@m"]),
    ])


def review_page(
    execution_id: str,
    data: dict[str, Any],
    errors: dict[str, str],
) -> dict[str, Any]:
    builder = data.get("builder", {})
    nodes: dict[str, Any] = builder.get("nodes", {})
    json_text = json.dumps(builder, indent=2)

    node_rows = "".join(
        f'<li>'
        + (f'<span uk-icon="icon:bolt;ratio:0.7" class="wf-node-start-icon"></span> ' if nid == builder.get("start") else "")
        + f'<code class="wf-node-id">{nid}</code> '
        + f'<span class="uk-label wf-node-type">{nconf.get("type", "") if isinstance(nconf, dict) else ""}</span>'
        + f'</li>'
        for nid, nconf in nodes.items()
    )

    preview_card = ui.raw(
        '<div class="uk-card uk-card-default uk-margin-bottom">'
        '<div class="uk-card-header uk-flex uk-flex-between uk-flex-middle">'
        '<span class="uk-text-muted uk-text-small">workflow definition</span>'
        '<div class="uk-flex wf-form-actions">'
        '<button class="uk-button uk-button-default uk-button-small" onclick="copyJson()" id="copy-btn">Copy JSON</button>'
        '<button class="uk-button uk-button-primary uk-button-small" onclick="downloadJson()">Download</button>'
        '</div></div>'
        '<div class="uk-card-body">'
        f'<pre id="workflow-json" class="wf-code-block">{json_text}</pre>'
        '</div></div>'
    )

    summary_card = ui.card(
        header=[ui.text("Summary", variant="muted")],
        body=[
            ui.raw(
                '<dl class="uk-description-list">'
                '<dt>Workflow ID</dt>'
                f'<dd><code>{builder.get("id", "—")}</code></dd>'
                '<dt>Start Node</dt>'
                f'<dd><code>{builder.get("start", "—")}</code></dd>'
                f'<dt>Nodes ({len(nodes)})</dt>'
                f'<dd><ul class="uk-list uk-list-divider">{node_rows}</ul></dd>'
                '</dl>'
            ),
            ui.raw(
                '<div class="uk-margin-top">'
                '<a href="/new" class="uk-button uk-button-default uk-width-1-1">Build another workflow</a>'
                '</div>'
            ),
        ],
    )

    return ui.page([
        ui.step_progress(["1 · Done", "2 · Done", "3 · Review"], active=2),
        ui.raw(
            f'<h1 class="uk-heading-small uk-margin-small-bottom">'
            f'Review &amp; export'
            f'<span class="uk-text-muted"> / {builder.get("id", "")}</span>'
            f'</h1>'
        ),
        ui.grid([[preview_card], [summary_card]], widths=["uk-width-2-3@m", "uk-width-1-3@m"]),
        ui.raw("""
<script>
function copyJson() {
    const text = document.getElementById('workflow-json').textContent;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.getElementById('copy-btn');
        const orig = btn.textContent;
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = orig; }, 1500);
    });
}
function downloadJson() {
    const text = document.getElementById('workflow-json').textContent;
    const id = """ + json.dumps(builder.get("id", "workflow")) + """;
    const blob = new Blob([text], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url;
    a.download = id + '.json'; a.click();
    URL.revokeObjectURL(url);
}
</script>"""),
    ])
