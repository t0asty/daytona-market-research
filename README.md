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

### OpenAI keys: what works best with Daytona

**Simplest reliable pattern (recommended):**

1. **Sandboxes = no OpenAI.** Run the YouTube worker in **`--mode playwright`** only. Daytona never sees your API key.
2. **Your laptop / CI = optional OpenAI.** Use **`report-gen --llm`** (or future local polish) with `OPENAI_API_KEY` in a **gitignored** `.env` or secret store—not in the repo, not in `.env.example`.

That avoids “key leaked / blocked” noise from **cloud datacenter IPs** and from keys accidentally appearing in **logs, screenshots, or public repos**.

**If you need an LLM inside a remote environment:**

- **Azure OpenAI** (or another **server-oriented** API) is often smoother than a consumer `sk-...` key from arbitrary cloud IPs.
- **Your own tiny proxy** (e.g. FastAPI on a host you control): the sandbox calls the proxy with a **short-lived token**; only the proxy holds `OPENAI_API_KEY`. Rotate if the token leaks, not the main key.
- **Never** commit real keys; **rotate** any key that was ever committed or pasted into chat.

There is no magic that maps **Daytona credits** to **OpenAI usage**—OpenAI bills tokens separately unless you use a bundled product from another vendor.

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

## Daytona: YouTube public listing worker (browser + allowlist)

This repo includes a **Playwright** worker that opens a **public** YouTube channel `/videos` URL, samples visible titles and view counts, and writes a single [`AgentFinding`](report_gen/models.py) JSON (`source_role: organic_social`). Optional **`browser-use`** mode uses an LLM-driven browser agent with the same JSON output contract when DOM scraping is too brittle.

### “Agents” inside Daytona (expectations vs this repo)

Daytona is positioned as a runtime for **AI agents**, but **agent** does not have to mean “LLM inside the sandbox.” In practice, an **agent worker** is often: **isolated sandbox → autonomous job → structured output**. That matches this worker: it runs **without an LLM** in default `--mode playwright`, still consumes **Daytona credits**, and still emits **`AgentFinding` JSON** for the report pipeline—so you are **using agents in Daytona** in the same sense as “one sandbox per channel job.”

If reviewers specifically want a **language model in the loop** inside the sandbox, you can:

- use **`--mode agent`** (browser-use) **only** once you have a **server-safe** model path (e.g. **Azure OpenAI**, or a **small proxy** that holds the provider key—not the raw key in sandbox env), or  
- follow Daytona’s own **orchestrated agent** examples (e.g. **RLM + LiteLLM** in their docs), where the **LLM plans** and **code runs in sandboxes**—still your provider billing, not “Daytona credits for tokens.”

Default **`playwright`** mode stays the best default when **OpenAI (or other) keys must not run from cloud sandboxes**.

### Install

```bash
pip install -e ".[worker]"          # Playwright scraper
playwright install chromium         # local runs outside Docker
# Optional agent mode:
pip install -e ".[browser-agent]"
```

### Run locally

```bash
social-youtube-worker \
  --channel-url "https://www.youtube.com/@YouTube/videos" \
  --max-items 10 \
  -o /tmp/social_snapshot.finding.json
# Optional: LLM + browser-use (needs OPENAI_API_KEY)
social-youtube-worker --mode agent --channel-url "https://www.youtube.com/@YouTube/videos" -o /tmp/out.json
```

**Mock YouTube (no network to youtube.com)** — demos or strict egress tiers:

```bash
social-youtube-worker --mock --channel-url "https://www.youtube.com/@YourBrand/videos" --max-items 5 -o /tmp/social_snapshot.finding.json
# or: export SOCIAL_YOUTUBE_MOCK=1
```

Synthetic output: `agent_id: mock-youtube`, low `confidence`, “MOCK” in headline/evidence.

### Mock B2B SaaS marketing agents (YC-style)

Three extra **`AgentFinding`** generators for paid search, organic SEO, and PLG funnel—no live APIs:

```bash
mock-saas-findings --role paid_search --company "YourStartup" -o /tmp/mock_paid_search.finding.json
mock-saas-findings --role organic_search --company "YourStartup" -o /tmp/mock_organic.finding.json
mock-saas-findings --role funnel --company "YourStartup" -o /tmp/mock_funnel.finding.json
# all three → ./mock_<role>.finding.json
mock-saas-findings --role all --company "YourStartup" --out-dir ./mock_findings
```

Merge into a report with `report-gen --inputs "mock_findings/*.json" "examples/fixtures/*.json" --out report.md`.

### Modular marketing orchestrator (sandbox-safe mocks)

One **agent id** per channel (YouTube, Google Ads, organic search, PLG funnel, Google Maps, LinkedIn, Meta Ads Library, G2/Capterra-style reviews). Implementations are **mock-only** so Daytona sandboxes without reliable outbound access still produce valid [`AgentFinding`](report_gen/models.py) JSON.

- **CLI:** `marketing-orchestrator list`, `run <id>`, `run-all`, `run-remote [agent_id|all]`
- **Programmatic:** `from orchestrator import ResearchContext, run_registered`
- **Daytona automation** uses the **Daytona Python SDK** (same idea as `report_gen/daytona_runner.py`), not Cursor’s Daytona MCP. Install `pip install -e ".[daytona]"`, set `DAYTONA_API_KEY`. Snapshot: `MARKETING_SNAPSHOT_NAME`, or fallback `SEO_SNAPSHOT_NAME`, then `seo-agent-v1`. The remote runner **uploads a minimal Python tree** (no `git clone`); it runs `pip install pydantic` inside the sandbox—pre-install `pydantic` in your snapshot if `pip` is blocked.

```bash
marketing-orchestrator list
marketing-orchestrator run youtube --company "Acme" --stdout-json
marketing-orchestrator run-all --company "Acme" --out-dir ./marketing_findings
marketing-orchestrator run-remote youtube --company "Acme" -o ./remote_youtube.finding.json
marketing-orchestrator run-remote all --company "Acme" --output-dir ./remote_findings
```

Feed merged inputs to `report-gen` as usual.

### Daytona: get code with **git** (simplest default)

If you are **not** using a pre-built snapshot, cloning this repo in the sandbox is usually easier than uploading a zip.

1. **`create_sandbox`** with outbound access to **Git** and **PyPI** (either leave allowlist open for the first run, or include domains such as `github.com, codeload.github.com, objects.githubusercontent.com, raw.githubusercontent.com, pypi.org, files.pythonhosted.org`). Add YouTube-related hosts when you run the scraper (see [Network allowlist](#network-allowlist-daytona-create_sandbox)). Playwright’s browser download may need extra hosts (e.g. `playwright.azureedge.net`, `storage.googleapis.com`) unless Chromium is already in the image.

2. **Clone** (pick one):

   - **MCP** `git_clone` with `url` + sandbox `id`, e.g. clone into `/tmp`; or  
   - **`execute_command`**:  
     `cd /tmp && git clone --depth 1 https://github.com/t0asty/daytona-market-research.git`

   Use **your fork’s URL** if you work from a fork. **Private repos:** configure Daytona/Git credentials for the sandbox (PAT, deploy key, or org integration)—plain `https://github.com/org/private.git` without auth will fail with a username/password prompt.

3. **Install and run** (vanilla Python image):

   **Restricted tier (no YouTube / limited internet):** mock only; needs Git + PyPI for `pip install -e .` (no Playwright download):

   ```bash
   cd /tmp/daytona-market-research
   MOCK=1 bash scripts/daytona_social_youtube_worker.sh
   ```

   **Full scrape** (Playwright, no LLM):

   ```bash
   cd /tmp/daytona-market-research
   bash scripts/daytona_social_youtube_worker.sh
   ```

   Overrides:

   ```bash
   cd /tmp/daytona-market-research
   CHANNEL_URL="https://www.youtube.com/@YourBrand/videos" MAX_ITEMS=5 MOCK=1 \
     bash scripts/daytona_social_youtube_worker.sh
   ```

   See [`scripts/daytona_social_youtube_worker.sh`](scripts/daytona_social_youtube_worker.sh). **Mock SaaS agents** in-sandbox (after `pip install -e .`):  
   `python -m workers.mock_agents.cli --role all --company YourStartup --out-dir /tmp/mock_findings`

4. **Pull the artifact** with MCP `file_download` (`filePath`: `/tmp/social_snapshot.finding.json` or your `OUTPUT`), then **`daytona-merge-report`** or **`report-gen`** on your machine.

For repeat runs, switch to a **[snapshot](#snapshot-image-daytona)** so you skip `pip` / `playwright install` every time.

### Snapshot image (Daytona)

**What you usually want:** the Dockerfile defines the **environment Daytona boots into** (a **snapshot**), not something you run *nested* inside an already-running sandbox.

1. **Local Docker (your machine)** — build and test, or push/tag for a registry if your Daytona setup pulls from there:

   ```bash
   docker build -f workers/social_public/Dockerfile -t daytona-social-youtube .
   ```

2. **Daytona snapshot (recommended for workers)** — register this Dockerfile as a snapshot in Daytona (dashboard or `daytona` CLI, depending on your org). Create sandboxes with that **snapshot** so Chromium + deps are already present; then you only **`execute_command`** the Python entrypoint (no `git clone` / `pip install` / `playwright install` on every run).

3. **Docker *inside* the sandbox** — only works if your Daytona **workspace template** actually provides a Docker daemon (Docker-in-Docker or a mounted socket). Most default sandboxes **do not**; `docker build` there will fail with “Cannot connect to the Docker daemon”. If yours does support it, you could `git clone` / upload the repo and run `docker build` + `docker run` like on any Linux VM—but that is heavier and rarer than using a prebuilt snapshot.

4. **API note** — Daytona’s `create_sandbox` can carry **`buildInfo.dockerfileContent`** (and context) so the **platform** builds the image when creating the sandbox; that is still “Daytona runs Docker,” not your process running Docker inside the guest.

**After the environment is ready** (snapshot or install), run:

```bash
python -m workers.social_public.cli \
  --channel-url "https://www.youtube.com/@YourBrand/videos" \
  -o /tmp/social_snapshot.finding.json
```

**Environment variables**

| Variable | When |
|----------|------|
| `OPENAI_API_KEY` | Required for `--mode agent` (ChatOpenAI + browser-use). |
| `OPENAI_MODEL` | Optional; default `gpt-4o-mini` for agent mode. |

### Network allowlist (Daytona `create_sandbox`)

Restrict egress with `networkAllowList` (comma-separated). YouTube listings typically touch domains such as:

`youtube.com, www.youtube.com, ytimg.com, ggpht.com, googlevideo.com, google.com`

Tune using your browser’s Network tab on a successful load; consent flows may call **google.com**. Thumbnails and streams often use **ytimg.com** / **googlevideo.com**.

### Handoff: pull JSON from sandbox → merged report

Preferred v1 path uses **MCP `file_download`** (or any copy of `/tmp/social_snapshot.finding.json`)—no public ingest URL required. Then merge with existing fixtures:

```bash
daytona-merge-report /path/to/social_snapshot.finding.json \
  --fixtures-glob "examples/fixtures/*.json" \
  --out report.md
```

Equivalent manual step:

```bash
report-gen --inputs "examples/fixtures/*.json" /path/to/social_snapshot.finding.json --out report.md
```

**HTTP push** remains an option later: a small FastAPI ingest on a **public URL** can accept POSTed JSON if you outgrow file download.

### Credits and lifecycle (~budget hygiene)

Sandboxes cost while they run. Defaults to keep in mind when calling Daytona:

- Use a **snapshot** with Chromium preinstalled (this Dockerfile) instead of reinstalling on every run.
- Set **`autoStopInterval`** / **`autoDeleteInterval`** appropriately; **`destroy_sandbox`** after you have downloaded the finding so nothing idles.
- **Agent mode** also consumes **LLM** tokens; shorter Playwright runs are cheaper on both dimensions.

### Sample finding

See [`examples/fixtures/organic_social_youtube.finding.json`](examples/fixtures/organic_social_youtube.finding.json) for the expected JSON shape (illustrative numbers).

### Tests

```bash
pip install -e ".[dev,worker]"
pytest
# Optional live YouTube smoke (network + Chromium):
RUN_YOUTUBE_INTEGRATION=1 pytest tests/test_social_worker.py -m integration
```
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
