import json
from pathlib import Path

from report_gen.merge import merge_findings, normalize_title
from report_gen.models import AgentFinding


def test_normalize_title() -> None:
    assert normalize_title("  Hello   World  ") == "hello world"


def test_dedupe_recommendations_case_insensitive() -> None:
    a = AgentFinding(
        source_role="paid_social",
        headline="h1",
        recommendations=[
            {
                "title": "Fix Creative Fatigue",
                "rationale": "From social",
            }
        ],
    )
    b = AgentFinding(
        source_role="paid_search",
        headline="h2",
        recommendations=[
            {
                "title": "fix creative fatigue",
                "rationale": "From search",
            }
        ],
    )
    merged = merge_findings([a, b])
    assert len(merged.merged_recommendations) == 1
    rec = merged.merged_recommendations[0]
    assert set(rec.sources) == {"paid_social", "paid_search"}
    assert "From social" in rec.rationale
    assert "From search" in rec.rationale or "paid_search" in rec.rationale


def test_sort_priority_impact_confidence() -> None:
    low = AgentFinding(
        source_role="a",
        headline="",
        recommendations=[
            {
                "title": "Low pri",
                "rationale": "x",
                "priority": 10,
                "impact_estimate": "low",
            }
        ],
        confidence=0.5,
    )
    high = AgentFinding(
        source_role="b",
        headline="",
        recommendations=[
            {
                "title": "High pri",
                "rationale": "y",
                "priority": 90,
                "impact_estimate": "high",
            }
        ],
        confidence=0.99,
    )
    merged = merge_findings([low, high])
    titles = [r.title for r in merged.merged_recommendations]
    assert titles[0] == "High pri"


def test_metric_rollup_side_by_side() -> None:
    a = AgentFinding(
        source_role="paid_social",
        headline="",
        metrics=[{"name": "Spend", "value": 100, "unit": "USD"}],
    )
    b = AgentFinding(
        source_role="paid_search",
        headline="",
        metrics=[{"name": "Spend", "value": 200, "unit": "USD"}],
    )
    merged = merge_findings([a, b])
    spend_rows = [r for r in merged.metric_rollup if r.name == "Spend"]
    assert len(spend_rows) == 1
    assert spend_rows[0].by_role == {"paid_social": 100, "paid_search": 200}


def test_fixtures_validate_and_merge() -> None:
    root = Path(__file__).resolve().parent.parent / "examples" / "fixtures"
    paths = sorted(root.glob("*.json"))
    assert paths
    findings = [AgentFinding.model_validate(json.loads(p.read_text())) for p in paths]
    merged = merge_findings(findings)
    assert merged.merged_recommendations
    # paid_social + paid_search share normalized "refresh top-fatigued creatives..."
    dup_titles = [
        r.title for r in merged.merged_recommendations if "refresh" in r.title.lower()
    ]
    assert len(dup_titles) == 1


def test_empty_findings() -> None:
    m = merge_findings([])
    assert "No agent" in m.executive_bullets[0]
