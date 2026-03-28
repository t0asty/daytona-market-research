from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from orchestrator.context import ResearchContext
from orchestrator.registry import AGENTS, list_agent_specs, run_registered
from orchestrator.uploads import repo_root


def _build_context(ns: argparse.Namespace) -> ResearchContext:
    if getattr(ns, "context_file", None):
        return ResearchContext.load_json_file(Path(ns.context_file))
    return ResearchContext(
        company=ns.company,
        domain=ns.domain or "",
        locale=ns.locale,
        max_items=ns.max_items,
        youtube_channel_url=ns.youtube_channel_url,
    )


def _env_set(name: str) -> str:
    return "set" if (os.environ.get(name) or "").strip() else "missing"


def cmd_doctor(_ns: argparse.Namespace) -> int:
    """Print whether expected env vars are present (never prints secret values)."""
    cwd_env = Path.cwd() / ".env"
    root_env = repo_root() / ".env"
    print("Local files:")
    print(f"  ./.env          {'found' if cwd_env.is_file() else 'not found'} ({cwd_env})")
    print(f"  repo/.env       {'found' if root_env.is_file() else 'not found'} ({root_env})")
    print("Environment (after your shell / CI exported or sourced a file):")
    print(f"  DAYTONA_API_KEY   {_env_set('DAYTONA_API_KEY')}")
    print(f"  OPENAI_API_KEY    {_env_set('OPENAI_API_KEY')}")
    try:
        from report_gen.daytona_imports import load_daytona

        load_daytona()
        print("  daytona-sdk       import ok (daytona or daytona_sdk)")
    except ImportError:
        print("  daytona-sdk       not installed (pip install -e \".[daytona]\")")
    snap = os.environ.get("MARKETING_SNAPSHOT_NAME") or os.environ.get("SEO_SNAPSHOT_NAME")
    if snap:
        print(f"  snapshot name     {snap} (MARKETING_SNAPSHOT_NAME or SEO_SNAPSHOT_NAME)")
    else:
        print("  snapshot name     (unset → default seo-agent-v1)")
    print()
    print("Tip: load keys into this shell, then re-run:")
    print("  set -a && source .env && set +a && marketing-orchestrator doctor")
    return 0


def cmd_list(_ns: argparse.Namespace) -> int:
    for spec in list_agent_specs():
        print(f"{spec.id}\t{spec.source_role}\t{spec.title}")
        print(f"  {spec.description}")
    return 0


def cmd_run(ns: argparse.Namespace) -> int:
    ctx = _build_context(ns)
    finding = run_registered(ns.agent_id, ctx)
    text = finding.model_dump_json(indent=2)
    if ns.stdout_json:
        print(text)
        return 0
    if ns.output:
        Path(ns.output).write_text(text + "\n", encoding="utf-8")
        return 0
    print(text)
    return 0


def cmd_run_all(ns: argparse.Namespace) -> int:
    ctx = _build_context(ns)
    out_dir = Path(ns.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for aid in sorted(AGENTS):
        finding = run_registered(aid, ctx)
        path = out_dir / f"{aid}.finding.json"
        path.write_text(finding.model_dump_json(indent=2) + "\n", encoding="utf-8")
        print(path)
    return 0


def cmd_run_remote(ns: argparse.Namespace) -> int:
    from orchestrator.remote_daytona import (
        daytona_configured,
        run_agent_in_daytona_sync,
        run_all_in_daytona_sync,
    )

    if not daytona_configured():
        print(
            "Daytona remote runs need DAYTONA_API_KEY and `pip install daytona-market-research[daytona]`.",
            file=sys.stderr,
        )
        return 2
    if ns.agent_id != "all" and ns.agent_id not in AGENTS:
        print(f"Unknown agent id {ns.agent_id!r}. Use 'all' or one of: {', '.join(sorted(AGENTS))}.", file=sys.stderr)
        return 2
    ctx = _build_context(ns)
    if ns.agent_id == "all":
        bundle = run_all_in_daytona_sync(ctx)
        if ns.output_dir:
            out = Path(ns.output_dir)
            out.mkdir(parents=True, exist_ok=True)
            for aid, row in bundle.items():
                (out / f"{aid}.finding.json").write_text(
                    json.dumps(row, indent=2) + "\n",
                    encoding="utf-8",
                )
                print(out / f"{aid}.finding.json")
        else:
            print(json.dumps(bundle, indent=2))
        return 0 if bundle else 1
    row = run_agent_in_daytona_sync(ns.agent_id, ctx)
    if row is None:
        return 1
    text = json.dumps(row, indent=2)
    if ns.stdout_json:
        print(text)
        return 0
    if ns.output:
        Path(ns.output).write_text(text + "\n", encoding="utf-8")
        return 0
    print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Marketing research orchestrator (mock agents, AgentFinding JSON output).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--company", default="Acme", help="Company / brand label for mocks")
    common.add_argument("--domain", default="", help="Primary domain for context in mocks")
    common.add_argument("--locale", default="en-US")
    common.add_argument("--max-items", type=int, default=10, help="e.g. YouTube mock row count")
    common.add_argument(
        "--youtube-channel-url",
        default=None,
        help="Override YouTube channel or /@handle/videos URL",
    )
    common.add_argument(
        "--context-file",
        default=None,
        help="JSON file with keys company, domain, locale, max_items, youtube_channel_url",
    )

    p_doctor = sub.add_parser(
        "doctor",
        help="Show env / SDK status (keys: set or missing only—values are never printed)",
    )
    p_doctor.set_defaults(func=cmd_doctor)

    p_list = sub.add_parser("list", help="Print registered agent ids and descriptions")
    p_list.set_defaults(func=cmd_list)

    p_run = sub.add_parser("run", parents=[common], help="Run one agent locally")
    p_run.add_argument("agent_id", choices=sorted(AGENTS))
    p_run.add_argument("-o", "--output", help="Write JSON to this file")
    p_run.add_argument(
        "--stdout-json",
        action="store_true",
        help="Print JSON only (for piping / Daytona log scrape)",
    )
    p_run.set_defaults(func=cmd_run)

    p_all = sub.add_parser("run-all", parents=[common], help="Run every agent locally")
    p_all.add_argument(
        "--out-dir",
        default="./marketing_findings",
        help="Directory for <agent_id>.finding.json files",
    )
    p_all.set_defaults(func=cmd_run_all)

    p_remote = sub.add_parser(
        "run-remote",
        parents=[common],
        help="Run agent(s) in Daytona (SDK). Snapshot: MARKETING_SNAPSHOT_NAME or SEO_SNAPSHOT_NAME.",
    )
    p_remote.add_argument(
        "agent_id",
        nargs="?",
        default="all",
        help="Agent id or 'all' for every registered agent (default: all)",
    )
    p_remote.add_argument(
        "-o",
        "--output",
        help="Write single-agent JSON result to this file",
    )
    p_remote.add_argument(
        "--output-dir",
        help="When agent_id is 'all', write one JSON file per agent here",
    )
    p_remote.add_argument("--stdout-json", action="store_true")
    p_remote.set_defaults(func=cmd_run_remote)

    ns = parser.parse_args(argv)
    return int(ns.func(ns))


if __name__ == "__main__":
    raise SystemExit(main())
