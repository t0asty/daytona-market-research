# daytona-market-research

Merge structured **agent findings** (JSON) into a single **marketing performance** Markdown report. Built for a split hackathon track: channel agents (e.g. in Daytona sandboxes) emit JSON; this repo merges and renders the report.

## Executive console (UI)

Browser UI: run **fixture-backed analyst agents** with one click, watch per-agent progress, read the merged report with styled markdown, and **download a PDF**.

```bash
# Terminal A — API (port 8000)
pip install -e ".[web]"
playwright install chromium
serve-report-ui
# or: python -m report_gen.web

# Terminal B — Vite dev server (proxies /api → 8000)
cd frontend && npm install && npm run dev
```

Open [http://localhost:5173](http://localhost:5173). **If you only open the API port (e.g. 8000):** with no built UI you’ll get a short HTML page at `/` explaining next steps; after `npm run build`, **`/` auto-serves `frontend/dist`** (no env var required when that folder exists). Override with `UI_STATIC_DIR` if needed.

```bash
cd frontend && npm install && npm run build
serve-report-ui   # then open http://127.0.0.1:8000/
```

Set `FINDINGS_FIXTURES_DIR` if your JSON findings live outside the repo default (`examples/fixtures`).

## Quick start (CLI)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
report-gen --inputs "examples/fixtures/*.json" --out report.md --merged-json merged.json
```

Optional LLM polish for the executive summary (requires API key and the `openai` extra):

```bash
pip install -e ".[llm]"
export OPENAI_API_KEY=...
report-gen --inputs "examples/fixtures/*.json" --out report.md --llm
```

## JSON contract (`AgentFinding`)

Each agent writes **one JSON object** per run. Teammates should validate against this shape (see [`report_gen/models.py`](report_gen/models.py), [`examples/fixtures/`](examples/fixtures/), and Jinja templates under [`report_gen/templates/`](report_gen/templates/)).

| Field | Required | Notes |
|--------|-----------|--------|
| `schema_version` | no (default `1`) | Bump when breaking the contract. |
| `source_role` | **yes** | Stable id, e.g. `paid_social`, `paid_search`, `funnel`. |
| `agent_id` | no | Your internal agent run id. |
| `period`, `as_of` | no | Shown in the report headers. |
| `headline` | **yes** | One-line takeaway for exec bullets. |
| `metrics[]` | no | `{ name, value, unit?, delta?, benchmark? }` — `value` / `delta` may be string or number. |
| `recommendations[]` | no | `{ title, rationale, impact_estimate?, effort?, priority? }` — `impact_estimate` / `effort` are `high` \| `medium` \| `low`; **higher `priority` sorts first**. |
| `evidence[]` | no | Bullet strings (citations, qualitative checks). |
| `confidence` | no | `0.0`–`1.0`, default `1.0`; used when ordering merged recommendations. |
| `raw_notes` | no | Longer text; shown in a collapsible block. **Not** trusted for new facts in the default (non-LLM) path. |

**Merging rules (deterministic):**

- Recommendations with the same **normalized title** (case/spacing-insensitive) are **merged**; sources and rationale are combined.
- Sort order: **priority** (desc), then **impact** (`high` > `medium` > `low`), then **max confidence** across contributing agents.
- Metrics with the same **name** are shown **side by side by `source_role`** — the merger does **not** sum or average across channels unless you do that in the agent.

## Library usage

```python
from pathlib import Path
import json
from report_gen import AgentFinding, merge_findings
from report_gen.render import render_report

findings = [
    AgentFinding.model_validate(json.loads(Path("f.json").read_text()))
]
merged = merge_findings(findings)
md = render_report(merged)
Path("out.md").write_text(md)
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```

Web API tests use FastAPI’s `TestClient` (included in the `dev` extra). Full PDF smoke test requires `playwright install chromium`.

## Later: Daytona orchestrator

When sandboxes produce `*.json` findings, point `report-gen --inputs` at that directory or pass multiple globs. If sandboxes run in Daytona Cloud, the mock API or collector they call must be on a **reachable URL** (not only `localhost`).
