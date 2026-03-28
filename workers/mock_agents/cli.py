from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from report_gen.models import AgentFinding

from workers.mock_agents.saas_b2b import (
    ROLE_ORDER,
    mock_funnel_plg_finding,
    mock_organic_search_finding,
    mock_paid_search_finding,
)

_BUILDERS: dict[str, Callable[..., AgentFinding]] = {
    "paid_search": mock_paid_search_finding,
    "organic_search": mock_organic_search_finding,
    "funnel": mock_funnel_plg_finding,
}


def _build(role: str, *, company: str) -> AgentFinding:
    fn = _BUILDERS.get(role)
    if fn is None:
        raise SystemExit(f"Unknown role {role!r}. Choose from: {', '.join(ROLE_ORDER)}")
    return fn(company=company)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit mock AgentFinding JSON for B2B SaaS marketing (demos / no live APIs).",
    )
    parser.add_argument(
        "--role",
        choices=[*ROLE_ORDER, "all"],
        required=True,
        help="Which mock agent to run, or 'all' to write one file per role.",
    )
    parser.add_argument(
        "--company",
        default="Acme",
        help='Startup / product name woven into copy (default: "Acme").',
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON path when --role is a single agent (required unless using --role all).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Directory for mock_<role>.finding.json when using --role all (default: cwd).",
    )
    parser.add_argument(
        "--print",
        dest="print_json",
        action="store_true",
        help="Also print JSON to stdout (single role only).",
    )
    args = parser.parse_args()

    company = args.company.strip() or "Acme"

    if args.role == "all":
        out_dir = args.out_dir or Path(".")
        out_dir.mkdir(parents=True, exist_ok=True)
        for role in ROLE_ORDER:
            finding = _build(role, company=company)
            path = out_dir / f"mock_{role}.finding.json"
            path.write_text(
                json.dumps(finding.model_dump(mode="json"), indent=2),
                encoding="utf-8",
            )
            print(f"Wrote {path}", file=sys.stderr)
        return

    if args.output is None:
        parser.error("--output/-o is required when --role is not 'all'.")

    finding = _build(args.role, company=company)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(finding.model_dump(mode="json"), indent=2), encoding="utf-8")
    print(f"Wrote {args.output}", file=sys.stderr)
    if args.print_json:
        print(json.dumps(finding.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
