from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

from report_gen.merge import merge_findings
from report_gen.models import AgentFinding
from report_gen.render import render_report


def _expand_inputs(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for p in patterns:
        matches = sorted(glob.glob(p, recursive=True))
        if matches:
            paths.extend(Path(m) for m in matches)
        else:
            path = Path(p)
            if path.is_file():
                paths.append(path)
    # stable unique
    seen: set[Path] = set()
    out: list[Path] = []
    for path in paths:
        rp = path.resolve()
        if rp not in seen:
            seen.add(rp)
            out.append(path)
    return out


def _load_findings(paths: list[Path]) -> list[AgentFinding]:
    findings: list[AgentFinding] = []
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        findings.append(AgentFinding.model_validate(raw))
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge agent finding JSON files into a single marketing report.",
    )
    parser.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help="Finding JSON files and/or glob patterns (e.g. examples/fixtures/*.json).",
    )
    parser.add_argument(
        "--out",
        default="report.md",
        help="Output markdown path (default: report.md).",
    )
    parser.add_argument(
        "--merged-json",
        dest="merged_json",
        default=None,
        help="Optional path to write MergedReport JSON.",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Polish Part 1 summary for non-experts via OpenAI (requires OPENAI_API_KEY and pip install '.[llm]').",
    )
    parser.add_argument(
        "--llm-model",
        default="gpt-4o-mini",
        help="OpenAI model id when --llm is set (default: gpt-4o-mini).",
    )
    args = parser.parse_args()

    paths = _expand_inputs(args.inputs)
    if not paths:
        print("No input files matched.", file=sys.stderr)
        sys.exit(1)

    findings = _load_findings(paths)
    merged = merge_findings(findings)

    if args.merged_json:
        Path(args.merged_json).write_text(
            json.dumps(merged.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

    executive_md: str | None = None
    if args.llm:
        from report_gen.llm_polish import polish_executive_summary

        executive_md = polish_executive_summary(merged, model=args.llm_model)

    report = render_report(merged, executive_summary_md=executive_md)
    Path(args.out).write_text(report, encoding="utf-8")
    print(f"Wrote {args.out}" + (f" and {args.merged_json}" if args.merged_json else ""))


if __name__ == "__main__":
    main()
