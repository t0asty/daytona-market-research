from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

from report_gen.merge import merge_findings
from report_gen.models import AgentFinding
from report_gen.render import render_report
from report_gen.web import state as state_mod
from report_gen.web.paths import resolve_fixtures_dir, resolve_frontend_dist_dir
from report_gen.web.pdf_export import markdown_to_html_document, render_pdf_bytes

app = FastAPI(title="Marketing report API", version="0.1.0")

_cors = os.environ.get("CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunResponse(BaseModel):
    ok: bool
    message: str = ""


def _load_fixtures() -> list[Path]:
    d = resolve_fixtures_dir()
    if not d.is_dir():
        raise FileNotFoundError(f"Fixtures directory not found: {d}")
    paths = sorted(d.glob("*.json"))
    if not paths:
        raise FileNotFoundError(f"No JSON fixtures in {d}")
    return paths


def _run_pipeline(paths: list[Path]) -> str:
    findings: list[AgentFinding] = []
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        findings.append(AgentFinding.model_validate(raw))
    merged = merge_findings(findings)
    return render_report(merged)


def _try_claim_run() -> bool:
    st = state_mod.state
    with st.lock:
        if st.running:
            return False
        st.running = True
        st.ready = False
        st.error = None
        st.markdown = ""
        return True


def _finish_run(*, success: bool, error: str | None = None) -> None:
    st = state_mod.state
    with st.lock:
        st.running = False
        if error is not None:
            st.error = error
        if not success:
            st.ready = False


async def _sse_daytona_run() -> AsyncIterator[bytes]:
    """Real Daytona sandbox execution — used when DAYTONA_API_KEY is set."""
    from report_gen.daytona_runner import run_daytona_agents

    st = state_mod.state
    fixtures_dir = resolve_fixtures_dir()

    try:
        async for event in run_daytona_agents(fixtures_dir):
            if event.get("type") == "report_ready":
                # Run the merge/render pipeline on the newly written findings
                try:
                    paths = sorted(fixtures_dir.glob("*.json"))
                    md = await asyncio.to_thread(_run_pipeline, paths)
                    with st.lock:
                        st.markdown = md
                        st.ready = True
                        st.running = False
                        st.error = None
                except Exception as e:
                    _finish_run(success=False, error=str(e))
                    yield _sse({"type": "error", "message": str(e)})
                    return
            yield _sse(event)
    except Exception as e:
        _finish_run(success=False, error=str(e))
        yield _sse({"type": "error", "message": str(e)})


# Keep original name as alias for fixture mode
async def _sse_agent_run() -> AsyncIterator[bytes]:
    st = state_mod.state
    try:
        paths = await asyncio.to_thread(_load_fixtures)
    except FileNotFoundError as e:
        _finish_run(success=False, error=str(e))
        yield _sse({"type": "error", "message": str(e)})
        return

    yield _sse({"type": "run_started", "total": len(paths)})

    delay = float(os.environ.get("AGENT_SIM_DELAY_SEC", "0.55"))

    try:
        for i, path in enumerate(paths):
            role = "unknown"
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                role = str(data.get("source_role", path.stem))
            except Exception:
                role = path.stem
            yield _sse({"type": "agent_started", "index": i, "role": role, "file": path.name})
            await asyncio.sleep(delay)
            yield _sse({"type": "agent_finished", "index": i, "role": role})

        yield _sse({"type": "merging"})

        md = await asyncio.to_thread(_run_pipeline, paths)
    except Exception as e:
        _finish_run(success=False, error=str(e))
        yield _sse({"type": "error", "message": str(e)})
        return

    with st.lock:
        st.markdown = md
        st.ready = True
        st.running = False
        st.error = None

    yield _sse({"type": "report_ready"})


def _sse(obj: dict) -> bytes:
    return f"data: {json.dumps(obj)}\n\n".encode("utf-8")


@app.get("/api/health")
def health() -> dict[str, str]:
    from report_gen.daytona_runner import is_daytona_available

    mode = "daytona" if is_daytona_available() else "fixtures"
    return {"status": "ok", "agent_mode": mode}


@app.get("/api/fixtures")
def list_fixtures() -> JSONResponse:
    try:
        paths = _load_fixtures()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    out = []
    for p in paths:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            out.append(
                {
                    "file": p.name,
                    "source_role": data.get("source_role", p.stem),
                    "headline": (data.get("headline") or "")[:160],
                }
            )
        except Exception:
            out.append({"file": p.name, "source_role": p.stem, "headline": ""})
    return JSONResponse({"fixtures": out, "directory": str(resolve_fixtures_dir())})


@app.get("/api/report")
def get_report() -> JSONResponse:
    st = state_mod.state
    with st.lock:
        return JSONResponse(
            {
                "ready": st.ready,
                "running": st.running,
                "markdown": st.markdown if st.ready else "",
                "error": st.error,
            }
        )


@app.post("/api/run", response_model=RunResponse)
async def run_analysis() -> RunResponse:
    return RunResponse(ok=True, message="Open GET /api/run/stream (SSE) to execute agents and build the report.")


@app.get("/api/run/stream")
async def run_stream() -> StreamingResponse:
    if not _try_claim_run():
        raise HTTPException(status_code=409, detail="A run is already in progress.")

    # Dispatch: real Daytona sandboxes if API key is set, fixture simulation otherwise
    use_daytona = bool(os.environ.get("DAYTONA_API_KEY"))
    runner = _sse_daytona_run() if use_daytona else _sse_agent_run()

    return StreamingResponse(
        runner,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _markdown_to_pdf_bytes(md: str) -> bytes:
    html = markdown_to_html_document(md)
    return render_pdf_bytes(html)


@app.get("/api/report.pdf")
async def download_pdf() -> Response:
    st = state_mod.state
    with st.lock:
        if not st.ready or not st.markdown:
            raise HTTPException(status_code=404, detail="No report yet. Run analysis first.")
        md = st.markdown

    try:
        pdf = await asyncio.to_thread(_markdown_to_pdf_bytes, md)
    except ImportError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF failed: {e}") from e

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="marketing-performance-report.pdf"',
        },
    )


_ROOT_HELP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Marketing report API</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem;
           line-height: 1.5; color: #1a1a1a; }
    code { background: #f4f4f5; padding: 0.15em 0.4em; border-radius: 4px; }
    a { color: #4f46e5; }
    li { margin: 0.35em 0; }
  </style>
</head>
<body>
  <h1>Marketing report API</h1>
  <p>This server exposes <code>/api/*</code> only. There is no UI bundle here yet.</p>
  <ul>
    <li><strong>Dev (recommended):</strong> run <code>npm run dev</code> in <code>frontend/</code>
      (Vite on port <strong>5173</strong> proxies <code>/api</code> to this process).</li>
    <li><strong>Single port:</strong> <code>cd frontend &amp;&amp; npm run build</code>, then restart the API —
      it will auto-serve <code>frontend/dist</code> at <code>/</code> when that folder exists.</li>
  </ul>
  <p>Quick links: <a href="/docs">OpenAPI docs</a> · <a href="/api/health">/api/health</a></p>
</body>
</html>"""


def _setup_ui() -> None:
    dist = resolve_frontend_dist_dir()
    if dist is not None:
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=str(dist), html=True), name="ui")
        return

    @app.get("/", include_in_schema=False)
    def _root_help() -> HTMLResponse:
        return HTMLResponse(content=_ROOT_HELP_HTML)


_setup_ui()
