from __future__ import annotations

from datetime import UTC, datetime

from report_gen.models import AgentFinding, Metric, Recommendation

_MOCK_EVIDENCE_PREFIX = (
    "MOCK DATA — synthetic B2B SaaS / YC-style scenario; not from live ad platforms or analytics."
)


def _as_of() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def mock_paid_search_finding(*, company: str = "Acme") -> AgentFinding:
    """High-intent search + competitor conquest narrative (Google Ads style)."""
    c = company.strip() or "Acme"
    return AgentFinding(
        schema_version=1,
        agent_id="mock-paid-search",
        source_role="paid_search",
        period="2026-Q1",
        as_of=_as_of(),
        headline=(
            f"Search demand for '{c}' category terms is healthy; brand impression share slipped "
            "while mid-funnel comparison queries grew—likely competitor spend."
        ),
        metrics=[
            Metric(name="Spend", value=58_400, unit="USD", delta=0.04),
            Metric(name="SQLs attributed (last-touch)", value=23, unit="count", delta=2),
            Metric(name="Blended CPL", value=412, unit="USD", delta=-0.06),
            Metric(name="Impression share (brand core)", value=68, unit="%", delta=-7),
            Metric(name="Impression share (comparison)", value=41, unit="%", delta=5),
        ],
        recommendations=[
            Recommendation(
                title="Ring-fence budget on bottom-of-funnel comparison keywords",
                rationale=(
                    f"ROAS on “vs {c}” and “{c} alternative” clusters beat generic dev-tool terms by 2.1×; "
                    "shift 12–15% budget from broad SaaS generics."
                ),
                impact_estimate="high",
                effort="low",
                priority=82,
            ),
            Recommendation(
                title="Launch defensive brand campaigns in EU time zones",
                rationale="Auction insights show a well-funded competitor winning top slot 6–11 UTC; "
                "small brand CPC cap prevents share bleed.",
                impact_estimate="medium",
                effort="low",
                priority=68,
            ),
        ],
        evidence=[
            _MOCK_EVIDENCE_PREFIX,
            f"Mock account: {c} — Search campaigns, last 28d.",
            "Query growth: +22% WoW on “API monitoring alternative” variants (simulated).",
        ],
        confidence=0.32,
        raw_notes="Replace with Google Ads / Search Console export when APIs or egress are available.",
    )


def mock_organic_search_finding(*, company: str = "Acme") -> AgentFinding:
    """SEO + content flywheel for a PLG devtool-style startup."""
    c = company.strip() or "Acme"
    return AgentFinding(
        schema_version=1,
        agent_id="mock-organic-search",
        source_role="organic_search",
        period="2026-Q1",
        as_of=_as_of(),
        headline=(
            f"Organic non-brand sessions up; top doc pages rank but “{c} pricing” and integration guides "
            "underperform vs a Series A peer on key comparison terms."
        ),
        metrics=[
            Metric(name="Organic sessions (non-brand)", value=41_200, unit="count", delta=0.11),
            Metric(name="Signups from organic (attributed)", value=312, unit="count", delta=0.08),
            Metric(name="Top-10 keywords (tracked)", value=84, unit="count", delta=6),
            Metric(name="Share of voice vs peer (comparison set)", value=38, unit="%", delta=-4),
        ],
        recommendations=[
            Recommendation(
                title="Ship three integration templates with canonical comparison URLs",
                rationale=(
                    f"Gaps on “{c} + Datadog” and similar drive high-intent traffic to competitor "
                    "docs; templates rank faster than homepage pivots."
                ),
                impact_estimate="high",
                effort="medium",
                priority=76,
            ),
            Recommendation(
                title="Refresh pricing and security pages for E-E-A-T signals",
                rationale="Mock crawl shows thin trust copy vs peer; add SOC2 snippet, customer logos, and FAQ schema.",
                impact_estimate="medium",
                effort="low",
                priority=61,
            ),
        ],
        evidence=[
            _MOCK_EVIDENCE_PREFIX,
            f"Mock property: marketing site for {c} — organic landing report.",
            "Simulated: pricing URL lost 4 positions on “transparent pricing API” cluster.",
        ],
        confidence=0.30,
        raw_notes="Replace with Search Console / Ahrefs / Semrush export when connected.",
    )


def mock_funnel_plg_finding(*, company: str = "Acme") -> AgentFinding:
    """Product-led growth funnel: signup → activation → trial conversion."""
    c = company.strip() or "Acme"
    return AgentFinding(
        schema_version=1,
        agent_id="mock-plg-funnel",
        source_role="funnel",
        period="2026-Q1",
        as_of=_as_of(),
        headline=(
            "Activation to “first API call” improved after onboarding tweak; trial-to-paid still trails "
            "YC benchmark—checkout friction on annual plan."
        ),
        metrics=[
            Metric(name="Visitor → signup rate", value=3.4, unit="%", delta=0.3),
            Metric(name="Signup → activated (7d)", value=28, unit="%", delta=2.1),
            Metric(name="Trial → paid (cohort)", value=9.2, unit="%", delta=-0.7),
            Metric(name="Net revenue retention (mock)", value=108, unit="%", delta=1.0),
        ],
        recommendations=[
            Recommendation(
                title="A/B default trial length vs credit-card-upfront annual",
                rationale="Mock funnel: 34% of drop-offs occur on billing step; annual toggle hidden below fold on mobile.",
                impact_estimate="high",
                effort="medium",
                priority=79,
            ),
            Recommendation(
                title="Trigger in-app checklist until first successful 200 from SDK",
                rationale="Users who complete SDK step in 24h convert 2.4×; push notification + email nudge at hour 6.",
                impact_estimate="high",
                effort="low",
                priority=74,
            ),
        ],
        evidence=[
            _MOCK_EVIDENCE_PREFIX,
            f"Mock product analytics: {c} — funnel and revenue (sample warehouse).",
            "Simulated cohort: Feb trials underperform Jan on mobile web only.",
        ],
        confidence=0.31,
        raw_notes="Replace with product analytics (e.g. Amplitude, Mixpanel, warehouse) when wired.",
    )


ROLE_ORDER: tuple[str, ...] = ("paid_search", "organic_search", "funnel")
