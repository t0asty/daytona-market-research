from __future__ import annotations

from datetime import UTC, datetime

from report_gen.models import AgentFinding, Metric, Recommendation

from orchestrator.context import ResearchContext

_MOCK = (
    "MOCK DATA — synthetic Meta Ads Library–style competitive read; not from live ad library scrapes."
)


def _as_of() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def run(ctx: ResearchContext) -> AgentFinding:
    c = ctx.company.strip() or "Acme"
    return AgentFinding(
        schema_version=1,
        agent_id="mock-meta-ads-library",
        source_role="meta_ads",
        period="2026-Q1",
        as_of=_as_of(),
        headline=(
            f"Competitors in {c}'s category rotate short UGC-style creatives weekly; "
            "mock signals suggest higher spend on retargeting than prospecting vs last quarter."
        ),
        metrics=[
            Metric(name="Distinct active advertisers (peer set)", value=9, unit="count", delta=1),
            Metric(name="New creatives / week (median)", value=4.2, unit="count", delta=0.8),
            Metric(name="Video share of new creatives", value=62, unit="%", delta=5),
            Metric(name="Estimated spend band (mock index)", value=72, unit="index", delta=-4),
        ],
        recommendations=[
            Recommendation(
                title="Refresh creative every 7–10 days on performance lanes",
                rationale="Mock library cadence shows fatigue after ~10 days for static comparison ads.",
                impact_estimate="high",
                effort="medium",
                priority=73,
            ),
            Recommendation(
                title="Test founder-led UGC hooks mirroring top peer themes",
                rationale="Three peers lead with workflow pain + screen capture; mock engagement indices skew there.",
                impact_estimate="medium",
                effort="low",
                priority=64,
            ),
        ],
        evidence=[
            _MOCK,
            f"Mock peer set anchored on {c} category keywords and landing domains.",
        ],
        confidence=0.26,
        raw_notes="Replace with Meta Ads Library exports or compliant third-party feeds when allowed.",
    )
