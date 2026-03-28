import json
from pathlib import Path

from report_gen.merge import merge_findings
from report_gen.models import AgentFinding
from report_gen.render import executive_bullet_humanize, humanize_role, oneline, render_report


def test_humanize_role() -> None:
    assert humanize_role("paid_social") == "Paid Social"
    assert humanize_role("paid_search") == "Paid Search"


def test_oneline_collapses_newlines() -> None:
    s = "a\n\nb  c\nd"
    assert oneline(s) == "a b c d"
    long = "x " * 200
    assert len(oneline(long)) <= 240
    assert oneline(long).endswith("…")


def test_executive_bullet_humanize() -> None:
    assert (
        executive_bullet_humanize("**paid_social**: Hello world.")
        == "**Paid Social**: Hello world."
    )
    assert executive_bullet_humanize("No match line") == "No match line"


def test_render_report_layered_sections() -> None:
    root = Path(__file__).resolve().parent.parent / "examples" / "fixtures"
    findings = [
        AgentFinding.model_validate(json.loads(p.read_text())) for p in sorted(root.glob("*.json"))
    ]
    merged = merge_findings(findings)
    md = render_report(merged)
    assert "## Part 1 — What to know first" in md
    assert "## Part 2 — Snapshot numbers" in md
    assert "## Part 3 — Ranked recommendations (full detail)" in md
    assert "## Part 4 — Cross-channel metrics (by role)" in md
    assert "## Part 5 — Findings by channel (evidence & tables)" in md
    assert "### Paid Social" in md or "### Paid social" in md
    assert "| # | Action |" in md


def test_render_empty_findings() -> None:
    md = render_report(merge_findings([]))
    assert "## Part 1 — What to know first" in md
    assert "_No prioritized recommendations were merged._" in md
