from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """
    Merge existing fixture findings with one JSON file pulled from a Daytona sandbox (file_download).

    Preferred handoff path: no public HTTP collector required — download the finding, then run this.
    """
    parser = argparse.ArgumentParser(
        description="Run report-gen with default fixtures plus one extra AgentFinding (e.g. from Daytona).",
    )
    parser.add_argument(
        "extra_finding",
        type=Path,
        help="Path to AgentFinding JSON (after MCP file_download or scp).",
    )
    parser.add_argument(
        "--fixtures-glob",
        default="examples/fixtures/*.json",
        help="Glob for baseline findings (default: examples/fixtures/*.json).",
    )
    parser.add_argument(
        "--out",
        default="report.md",
        help="Output markdown path (default: report.md).",
    )
    parser.add_argument(
        "--merged-json",
        default=None,
        help="Optional path to write merged JSON (passed through to report-gen).",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Forward --llm to report-gen (requires OPENAI_API_KEY).",
    )
    args = parser.parse_args()

    if not args.extra_finding.is_file():
        print(f"Not a file: {args.extra_finding}", file=sys.stderr)
        sys.exit(1)

    cmd = [
        sys.executable,
        "-m",
        "report_gen.cli",
        "--inputs",
        args.fixtures_glob,
        str(args.extra_finding.resolve()),
        "--out",
        args.out,
    ]
    if args.merged_json:
        cmd.extend(["--merged-json", args.merged_json])
    if args.llm:
        cmd.append("--llm")

    proc = subprocess.run(cmd, check=False)
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
