from __future__ import annotations

from datetime import UTC, datetime

from report_gen.models import AgentFinding, Metric, Recommendation

from orchestrator.context import ResearchContext

_MOCK = (
    "MOCK DATA — synthetic G2 / Capterra-style scores; not from live review site pages or APIs."
)


def _as_of() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def run(ctx: ResearchContext) -> AgentFinding:
    c = ctx.company.strip() or "Acme"
    return AgentFinding(
        schema_version=1,
        agent_id="mock-review-aggregators",
        source_role="review_aggregators",
        period="2026-Q1",
        as_of=_as_of(),
        headline=(
            f"{c} holds a strong overall score but trails on “ease of setup” vs a well-funded rival; "
            "recent reviews mention onboarding time more than pricing."
        ),
        metrics=[
            Metric(name="G2 overall (mock)", value=4.5, unit="stars", delta=0.1),
            Metric(name="Capterra overall (mock)", value=4.4, unit="stars", delta=0.0),
            Metric(name="Category rank (mock)", value=7, unit="rank", delta=-1),
            Metric(name="Reviews mentioning onboarding (90d)", value=23, unit="%", delta=5),
        ],
        recommendations=[
            Recommendation(
                title="Ship a guided “first value in 15 minutes” checklist and link it in review responses",
                rationale="Mock text clustering flags setup friction as the dominant negative theme.",
                impact_estimate="high",
                effort="medium",
                priority=78,
            ),
            Recommendation(
                title="Run a targeted review campaign with long-tenure happy customers",
                rationale="Score is stable but volume is below category median; recency helps conversion from search.",
                impact_estimate="medium",
                effort="low",
                priority=62,
            ),
        ],
        evidence=[
            _MOCK,
            f"Mock profiles: {c} on G2 and Capterra grids.",
        ],
        confidence=0.29,
        raw_notes="Replace with G2/Capterra API or CSV exports when connected.",
    )
