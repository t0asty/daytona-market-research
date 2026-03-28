from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from orchestrator.context import ResearchContext
from orchestrator.uploads import minimal_python_relative_paths, repo_root, validate_minimal_tree
from report_gen.daytona_imports import load_daytona, sdk_installed

logger = logging.getLogger(__name__)


def marketing_snapshot_name() -> str:
    return os.environ.get(
        "MARKETING_SNAPSHOT_NAME",
        os.environ.get("SEO_SNAPSHOT_NAME", "seo-agent-v1"),
    )


def daytona_configured() -> bool:
    if not os.environ.get("DAYTONA_API_KEY"):
        return False
    return sdk_installed()


async def run_agent_in_daytona(agent_id: str, ctx: ResearchContext) -> dict[str, Any] | None:
    """Run one registered agent in a Daytona sandbox and return ``AgentFinding`` as dict.

    Uploads a minimal Python tree (no git clone), installs ``pydantic``, runs
    ``python -m orchestrator run … --stdout-json``. Uses the same snapshot pattern as
    ``report_gen.daytona_runner``; pre-bake ``pydantic`` in the snapshot if outbound ``pip`` is blocked.
    """
    d = load_daytona()
    CreateSandboxFromSnapshotParams = d.CreateSandboxFromSnapshotParams
    FileUpload = d.FileUpload
    Daytona = d.Daytona
    DaytonaConfig = d.DaytonaConfig

    validate_minimal_tree()
    root = repo_root()
    snapshot = marketing_snapshot_name()

    uploads: list[Any] = []
    for rel in minimal_python_relative_paths():
        src = root / rel
        uploads.append(
            FileUpload(
                source=src.read_bytes(),
                destination=f"/home/daytona/{rel}",
            )
        )
    ctx_path = "/home/daytona/orchestrator_context.json"
    uploads.append(
        FileUpload(
            source=json.dumps(ctx.to_json_dict(), indent=2).encode(),
            destination=ctx_path,
        )
    )

    daytona = Daytona(
        DaytonaConfig(
            api_key=os.environ["DAYTONA_API_KEY"],
            api_url=os.environ.get("DAYTONA_API_URL", "https://app.daytona.io/api"),
            target=os.environ.get("DAYTONA_TARGET", "us"),
        )
    )

    sandbox = None
    try:
        sandbox = await asyncio.to_thread(
            daytona.create,
            CreateSandboxFromSnapshotParams(
                snapshot=snapshot,
                language="python",
                env_vars={
                    "MARKETING_AGENT_ID": agent_id,
                    "PYTHONUNBUFFERED": "1",
                },
                labels={"agent": agent_id, "platform": "daytona-market-research"},
                auto_stop_interval=int(os.environ.get("MARKETING_SANDBOX_AUTO_STOP_MIN", "20")),
                auto_archive_interval=int(os.environ.get("MARKETING_SANDBOX_AUTO_ARCHIVE_MIN", "60")),
                auto_delete_interval=int(os.environ.get("MARKETING_SANDBOX_AUTO_DELETE_MIN", "120")),
            ),
            timeout=120,
        )
        logger.info("Sandbox %s for marketing agent %s", sandbox.id, agent_id)

        await asyncio.to_thread(sandbox.fs.upload_files, uploads)

        await asyncio.to_thread(
            sandbox.process.exec,
            "pip install -q 'pydantic>=2.5' 2>/dev/null || true",
            cwd="/home/daytona",
            timeout=120,
        )

        cmd = (
            "export PYTHONPATH=/home/daytona && "
            f"python -m orchestrator run {agent_id} "
            f"--context-file {ctx_path} --stdout-json"
        )
        exec_result = await asyncio.to_thread(
            sandbox.process.exec,
            cmd,
            cwd="/home/daytona",
            timeout=180,
        )
        if exec_result.exit_code != 0:
            logger.error(
                "Agent %s exited %s: %s",
                agent_id,
                exec_result.exit_code,
                (exec_result.result or "")[:800],
            )
            return None

        output = (exec_result.result or "").strip()
        json_start = output.rfind("{")
        json_end = output.rfind("}") + 1
        if json_start == -1 or json_end == 0:
            logger.error("No JSON in sandbox output: %s", output[:400])
            return None
        return json.loads(output[json_start:json_end])
    except Exception as exc:
        logger.exception("Daytona run failed for %s: %s", agent_id, exc)
        return None
    finally:
        if sandbox:
            try:
                await asyncio.to_thread(daytona.delete, sandbox)
            except Exception as del_exc:
                logger.warning("Sandbox cleanup failed: %s", del_exc)


def run_agent_in_daytona_sync(agent_id: str, ctx: ResearchContext) -> dict[str, Any] | None:
    return asyncio.run(run_agent_in_daytona(agent_id, ctx))


async def run_all_in_daytona(ctx: ResearchContext) -> dict[str, dict[str, Any]]:
    """Run every registered agent sequentially in its own sandbox (simple, predictable billing)."""
    from orchestrator.registry import AGENTS

    out: dict[str, dict[str, Any]] = {}
    for aid in sorted(AGENTS):
        row = await run_agent_in_daytona(aid, ctx)
        if row is not None:
            out[aid] = row
    return out


def run_all_in_daytona_sync(ctx: ResearchContext) -> dict[str, dict[str, Any]]:
    return asyncio.run(run_all_in_daytona(ctx))
