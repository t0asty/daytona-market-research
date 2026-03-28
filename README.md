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

Optional LLM polish for the Part 1 opening summary (non-expert audience; requires API key and the `openai` extra):

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

## Daytona-powered SEO research (live agent mode)

When `DAYTONA_API_KEY` is set, the "Run analyst agents" button spawns **real Daytona Cloud sandboxes** instead of reading static fixtures. Each sandbox executes an SEO research script and produces an `AgentFinding` JSON.

### Setup

```bash
pip install -e ".[web,daytona]"
cp .env.example .env
# Edit .env: set DAYTONA_API_KEY, SEO_DEFAULT_DOMAIN, SEO_DEFAULT_KEYWORDS

# Create the SEO snapshot (one-time)
python -m report_gen.daytona_snapshot

# Start the UI
serve-report-ui
```

### Pipeline stages

| # | Stage | What it does | Runs in |
|---|-------|-------------|---------|
| 1 | `keyword_research` | Google Suggest scraping, intent clustering | Sequential |
| 2 | `serp_analysis` | SERP fetching, position/feature detection | Sequential |
| 3 | `competitor_analysis` | Competitor page structure, content gaps | Parallel |
| 4 | `content_audit` | Sitemap crawl, on-page SEO checks | Parallel |
| 5 | `technical_seo` | 7 technical health checks | Parallel |
| 6 | `assessment` | Cross-agent compilation, executive summary | Sequential |

### How it works

```
Click "Run analyst agents"
    → server.py detects DAYTONA_API_KEY
    → daytona_runner.py spawns sandboxes for each stage
    → Each sandbox runs an seo_agents/*.py script
    → Findings written to FINDINGS_FIXTURES_DIR as *.finding.json
    → SSE events stream to React frontend (same format as fixture mode)
    → merge_findings() + render_report() produce the markdown
    → Frontend renders the report
```

Without `DAYTONA_API_KEY`, the UI falls back to the original fixture-based simulation. The SEO fixture examples (`examples/fixtures/keyword_research.finding.json`, etc.) demonstrate the output format.
