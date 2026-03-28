from __future__ import annotations

from datetime import UTC, datetime

from report_gen.models import AgentFinding, Metric, Recommendation

from orchestrator.context import ResearchContext

_MOCK = (
    "MOCK DATA — synthetic local / Maps scenario; not from Google Business Profile or Maps APIs."
)


def _as_of() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def run(ctx: ResearchContext) -> AgentFinding:
    c = ctx.company.strip() or "Acme"
    dom = (ctx.domain or "example.com").strip() or "example.com"
    return AgentFinding(
        schema_version=1,
        agent_id="mock-google-maps",
        source_role="google_maps",
        period="2026-Q1",
        as_of=_as_of(),
        headline=(
            f"{c} appears in the local pack for 6 high-intent “near me” queries; "
            f"review velocity lags a regional peer while {dom} branded search stays strong."
        ),
        metrics=[
            Metric(name="Local pack appearances (tracked queries)", value=6, unit="count", delta=1),
            Metric(name="Average Maps rating", value=4.2, unit="stars", delta=0.0),
            Metric(name="Reviews (90d)", value=14, unit="count", delta=-3),
            Metric(name="Photo engagement vs peer", value=71, unit="%", delta=-8),
        ],
        recommendations=[
            Recommendation(
                title="Run a 30-day review prompt after in-person or success milestones",
                rationale="Mock data shows competitor outpacing on recency; GBP posts alone do not close the gap.",
                impact_estimate="medium",
                effort="low",
                priority=66,
            ),
            Recommendation(
                title="Align GBP categories with top converting “near me” head terms",
                rationale="One category mismatch may suppress pack eligibility for two money keywords.",
                impact_estimate="high",
                effort="low",
                priority=71,
            ),
        ],
        evidence=[
            _MOCK,
            f"Mock entity: {c} — primary location + service area.",
            f"Website / domain context: {dom}",
        ],
        confidence=0.28,
        raw_notes="Replace with GBP / Maps APIs or Location insights export when egress and auth allow.",
    )
