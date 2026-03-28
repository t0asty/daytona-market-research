from __future__ import annotations

from datetime import UTC, datetime

from report_gen.models import AgentFinding, Metric, Recommendation

from orchestrator.context import ResearchContext

_MOCK = (
    "MOCK DATA — synthetic LinkedIn company page signals; not from LinkedIn APIs or live HTML."
)


def _as_of() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def run(ctx: ResearchContext) -> AgentFinding:
    c = ctx.company.strip() or "Acme"
    return AgentFinding(
        schema_version=1,
        agent_id="mock-linkedin-company",
        source_role="linkedin_organic",
        period="2026-Q1",
        as_of=_as_of(),
        headline=(
            f"{c} page follower growth is steady; organic post reach dipped after algorithm-weighting change "
            "while employee reshares still outperform brand-only posts."
        ),
        metrics=[
            Metric(name="New followers (28d)", value=420, unit="count", delta=0.05),
            Metric(name="Median organic reach / post", value=3_800, unit="count", delta=-0.12),
            Metric(name="Engagement rate (company posts)", value=2.1, unit="%", delta=0.0),
            Metric(name="Employee advocacy posts (28d)", value=37, unit="count", delta=4),
        ],
        recommendations=[
            Recommendation(
                title="Package customer proof as short native video for the feed",
                rationale="Mock mix: video and document carousels show 1.4× reach vs link posts in this sector.",
                impact_estimate="medium",
                effort="medium",
                priority=63,
            ),
            Recommendation(
                title="Coordinate launch moments with 3–5 exec + eng amplifiers",
                rationale="Spikes in employee reshares correlate with mock lead-form assists on flagship posts.",
                impact_estimate="high",
                effort="low",
                priority=77,
            ),
        ],
        evidence=[
            _MOCK,
            f"Mock page: {c} — organic and follower time series.",
        ],
        confidence=0.27,
        raw_notes="Replace with LinkedIn Marketing API or approved exports when available.",
    )
