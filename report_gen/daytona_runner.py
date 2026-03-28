"""Daytona-powered SEO agent runner.

Spawns real Daytona Cloud sandboxes for each SEO research stage,
executes agent scripts, collects AgentFinding JSON, and yields
SSE-compatible events matching the existing server.py format.

Falls back gracefully if Daytona SDK is not installed.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Agent stages in execution order
STAGES = [
    "keyword_research",
    "serp_analysis",
    "competitor_analysis",
    "content_audit",
    "technical_seo",
    "assessment",
]

# Stages that can run in parallel (independent of each other)
PARALLEL_STAGES = {"competitor_analysis", "content_audit", "technical_seo"}

# Locate the seo_agents scripts directory
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "seo_agents"


def is_daytona_available() -> bool:
    """Check if Daytona SDK is installed and API key is configured."""
    if not os.environ.get("DAYTONA_API_KEY"):
        return False
    from report_gen.daytona_imports import sdk_installed

    return sdk_installed()


def _get_seo_config() -> dict[str, Any]:
    """Build SEO research config from environment variables."""
    domain = os.environ.get("SEO_DEFAULT_DOMAIN", "example.com")
    keywords_raw = os.environ.get("SEO_DEFAULT_KEYWORDS", "")
    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
    competitors_raw = os.environ.get("SEO_DEFAULT_COMPETITORS", "")
    competitors = [c.strip() for c in competitors_raw.split(",") if c.strip()]

    return {
        "domain": domain,
        "seed_keywords": keywords,
        "competitors": competitors,
        "locale": os.environ.get("SEO_LOCALE", "en-US"),
        "max_keywords": int(os.environ.get("SEO_MAX_KEYWORDS", "50")),
        "max_pages_crawl": int(os.environ.get("SEO_MAX_PAGES", "20")),
    }


async def _run_stage(
    daytona_client,
    stage_name: str,
    input_data: dict[str, Any],
    fixtures_dir: Path,
) -> dict[str, Any] | None:
    """Run a single SEO agent stage in a Daytona sandbox.

    Returns the AgentFinding dict on success, None on failure.
    """
    from report_gen.daytona_imports import load_daytona

    d = load_daytona()
    CreateSandboxFromSnapshotParams = d.CreateSandboxFromSnapshotParams
    FileUpload = d.FileUpload

    script_path = _SCRIPTS_DIR / f"{stage_name}.py"
    common_path = _SCRIPTS_DIR / "common.py"
    reqs_path = _SCRIPTS_DIR / "requirements.txt"

    if not script_path.exists():
        logger.error("Script not found: %s", script_path)
        return None

    snapshot_name = os.environ.get("SEO_SNAPSHOT_NAME", "seo-agent-v1")

    sandbox = None
    try:
        sandbox = await asyncio.to_thread(
            daytona_client.create,
            CreateSandboxFromSnapshotParams(
                snapshot=snapshot_name,
                language="python",
                env_vars={"AGENT_ROLE": "seo", "STAGE": stage_name},
                labels={"stage": stage_name, "platform": "daytona-market-research"},
                auto_stop_interval=30,
                auto_archive_interval=60,
                auto_delete_interval=120,
            ),
            timeout=120,
        )
        logger.info("Sandbox %s created for stage '%s'", sandbox.id, stage_name)

        # Upload scripts
        files_to_upload = [
            FileUpload(
                source=script_path.read_bytes(),
                destination=f"/home/daytona/{script_path.name}",
            ),
            FileUpload(
                source=json.dumps(input_data).encode(),
                destination="/home/daytona/input.json",
            ),
        ]
        if common_path.exists():
            files_to_upload.append(
                FileUpload(source=common_path.read_bytes(), destination="/home/daytona/common.py")
            )
        if reqs_path.exists():
            files_to_upload.append(
                FileUpload(source=reqs_path.read_bytes(), destination="/home/daytona/requirements.txt")
            )

        await asyncio.to_thread(sandbox.fs.upload_files, files_to_upload)

        # Install deps (skip if snapshot already has them)
        await asyncio.to_thread(
            sandbox.process.exec,
            "pip install -q -r /home/daytona/requirements.txt 2>/dev/null || true",
            cwd="/home/daytona",
            timeout=120,
        )

        # Execute agent script
        exec_result = await asyncio.to_thread(
            sandbox.process.exec,
            f"python /home/daytona/{script_path.name}",
            cwd="/home/daytona",
            timeout=300,
        )

        if exec_result.exit_code != 0:
            raise RuntimeError(
                f"Script exited with code {exec_result.exit_code}: "
                f"{(exec_result.result or '')[:500]}"
            )

        # Parse AgentFinding JSON from stdout
        output = (exec_result.result or "").strip()
        json_start = output.rfind("{")
        json_end = output.rfind("}") + 1
        if json_start == -1 or json_end == 0:
            raise RuntimeError(f"No JSON found in output: {output[:200]}")

        finding = json.loads(output[json_start:json_end])

        # Write finding to fixtures directory
        fixtures_dir.mkdir(parents=True, exist_ok=True)
        finding_path = fixtures_dir / f"{stage_name}.finding.json"
        finding_path.write_text(json.dumps(finding, indent=2), encoding="utf-8")

        logger.info("Stage '%s' completed: %s", stage_name, finding.get("headline", ""))
        return finding

    except Exception as exc:
        logger.error("Stage '%s' failed: %s", stage_name, exc)
        return None

    finally:
        if sandbox:
            try:
                await asyncio.to_thread(daytona_client.delete, sandbox)
            except Exception as del_exc:
                logger.warning("Sandbox cleanup failed: %s", del_exc)


async def run_daytona_agents(fixtures_dir: Path) -> AsyncIterator[dict]:
    """Run SEO agents in Daytona sandboxes, yielding SSE events.

    Events match the format expected by server.py and the React frontend:
      {"type": "run_started", "total": N}
      {"type": "agent_started", "index": i, "role": role}
      {"type": "agent_finished", "index": i, "role": role}
      {"type": "merging"}
      {"type": "report_ready"}
      {"type": "error", "message": "..."}
    """
    from report_gen.daytona_imports import load_daytona

    d = load_daytona()
    Daytona = d.Daytona
    DaytonaConfig = d.DaytonaConfig

    config = _get_seo_config()

    try:
        daytona = Daytona(DaytonaConfig(
            api_key=os.environ["DAYTONA_API_KEY"],
            api_url=os.environ.get("DAYTONA_API_URL", "https://app.daytona.io/api"),
            target=os.environ.get("DAYTONA_TARGET", "us"),
        ))
    except Exception as exc:
        yield {"type": "error", "message": f"Daytona init failed: {exc}"}
        return

    # Clear previous findings
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    for old in fixtures_dir.glob("*.finding.json"):
        old.unlink()

    yield {"type": "run_started", "total": len(STAGES)}

    findings: dict[str, dict] = {}
    stage_index = {name: i for i, name in enumerate(STAGES)}

    # Stage 1: keyword_research
    yield {"type": "agent_started", "index": 0, "role": "keyword_research"}
    kw_input = {
        "domain": config["domain"],
        "seed_keywords": config.get("seed_keywords", []),
        "locale": config.get("locale", "en-US"),
        "max_keywords": config.get("max_keywords", 50),
    }
    kw_finding = await _run_stage(daytona, "keyword_research", kw_input, fixtures_dir)
    if kw_finding:
        findings["keyword_research"] = kw_finding
    yield {"type": "agent_finished", "index": 0, "role": "keyword_research"}

    # Stage 2: serp_analysis
    yield {"type": "agent_started", "index": 1, "role": "serp_analysis"}
    serp_input = {
        "domain": config["domain"],
        "keywords": kw_finding.get("_keywords", config.get("seed_keywords", [])) if kw_finding else config.get("seed_keywords", []),
    }
    serp_finding = await _run_stage(daytona, "serp_analysis", serp_input, fixtures_dir)
    if serp_finding:
        findings["serp_analysis"] = serp_finding
    yield {"type": "agent_finished", "index": 1, "role": "serp_analysis"}

    # Stages 3/4/5: parallel
    parallel_configs = {
        "competitor_analysis": {
            "domain": config["domain"],
            "competitors": config.get("competitors", []),
            "serp_data": serp_finding or {},
        },
        "content_audit": {
            "domain": config["domain"],
            "max_pages": config.get("max_pages_crawl", 20),
        },
        "technical_seo": {
            "domain": config["domain"],
        },
    }

    for stage in ["competitor_analysis", "content_audit", "technical_seo"]:
        yield {"type": "agent_started", "index": stage_index[stage], "role": stage}

    parallel_results = await asyncio.gather(
        _run_stage(daytona, "competitor_analysis", parallel_configs["competitor_analysis"], fixtures_dir),
        _run_stage(daytona, "content_audit", parallel_configs["content_audit"], fixtures_dir),
        _run_stage(daytona, "technical_seo", parallel_configs["technical_seo"], fixtures_dir),
    )

    for stage, result in zip(["competitor_analysis", "content_audit", "technical_seo"], parallel_results):
        if result:
            findings[stage] = result
        yield {"type": "agent_finished", "index": stage_index[stage], "role": stage}

    # Stage 6: assessment
    yield {"type": "agent_started", "index": 5, "role": "assessment"}
    assessment_input = {
        "domain": config["domain"],
        "findings": findings,
    }
    assessment_finding = await _run_stage(daytona, "assessment", assessment_input, fixtures_dir)
    if assessment_finding:
        findings["assessment"] = assessment_finding
    yield {"type": "agent_finished", "index": 5, "role": "assessment"}

    yield {"type": "merging"}
    yield {"type": "report_ready"}
