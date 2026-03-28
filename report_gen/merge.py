from __future__ import annotations

from collections import defaultdict

from report_gen.models import (
    AgentFinding,
    ImpactLevel,
    MergedRecommendation,
    MergedReport,
    MetricRollupRow,
    MetricValue,
    Recommendation,
)


def normalize_title(title: str) -> str:
    return " ".join(title.strip().lower().split())


def _impact_rank(level: ImpactLevel | None) -> int:
    if level is None:
        return 0
    return {"high": 3, "medium": 2, "low": 1}[level]


def _effort_rank(level: str | None) -> int:
    """Higher rank = lower effort (prefer showcasing quick wins in merges)."""
    if level is None:
        return 0
    return {"low": 3, "medium": 2, "high": 1}.get(level, 0)


def _better_impact(a: ImpactLevel | None, b: ImpactLevel | None) -> ImpactLevel | None:
    return a if _impact_rank(a) >= _impact_rank(b) else b


def _better_effort(a: str | None, b: str | None) -> str | None:
    return a if _effort_rank(a) >= _effort_rank(b) else b


def _rec_sort_key(rec: MergedRecommendation) -> tuple[int, int, int, float]:
    pri = rec.priority if rec.priority is not None else 0
    impact = _impact_rank(rec.impact_estimate)
    conf = rec.source_confidence
    return (pri, impact, int(conf * 1000), conf)


def _merge_two_recs(
    base: MergedRecommendation,
    other: Recommendation,
    other_role: str,
    other_title_display: str,
) -> MergedRecommendation:
    sources = list(dict.fromkeys([*base.sources, other_role]))
    if other.title.strip() != base.title.strip():
        see = list(dict.fromkeys([*base.see_also, other_title_display]))
    else:
        see = list(base.see_also)

    rationale = base.rationale
    o_rat = other.rationale.strip()
    if o_rat and o_rat not in rationale:
        rationale = f"{rationale}\n\n_(Also noted by **{other_role}**):_ {o_rat}"

    prios = [p for p in (base.priority, other.priority) if p is not None]
    merged_priority = max(prios) if prios else None
    return MergedRecommendation(
        title=base.title,
        rationale=rationale.strip(),
        sources=sources,
        impact_estimate=_better_impact(base.impact_estimate, other.impact_estimate),
        effort=_better_effort(base.effort, other.effort),
        priority=merged_priority,
        see_also=see,
        source_confidence=base.source_confidence,
    )


def merge_findings(findings: list[AgentFinding]) -> MergedReport:
    """Validate, dedupe recommendations, roll up metrics side-by-side, build exec bullets."""
    if not findings:
        return MergedReport(
            findings=[],
            merged_recommendations=[],
            metric_rollup=[],
            executive_bullets=["No agent findings were provided."],
        )

    by_name: dict[str, dict[str, MetricValue]] = defaultdict(dict)
    delta_by_name: dict[str, dict[str, MetricValue]] = defaultdict(dict)
    unit_by_name: dict[str, str | None] = {}

    for f in findings:
        for m in f.metrics:
            key = m.name.strip()
            by_name[key][f.source_role] = m.value
            if m.delta is not None:
                delta_by_name[key][f.source_role] = m.delta
            if m.unit is not None:
                unit_by_name[key] = m.unit
            elif key not in unit_by_name:
                unit_by_name[key] = None

    metric_rollup = [
        MetricRollupRow(
            name=name,
            unit=unit_by_name.get(name),
            by_role=dict(roles),
            delta_by_role=dict(delta_by_name.get(name, {})),
        )
        for name, roles in sorted(by_name.items(), key=lambda x: x[0].lower())
    ]

    buckets: dict[str, list[tuple[Recommendation, str, float]]] = defaultdict(list)
    for f in findings:
        for r in f.recommendations:
            buckets[normalize_title(r.title)].append((r, f.source_role, f.confidence))

    merged: list[MergedRecommendation] = []
    for _norm, group in buckets.items():
        first, role0, conf0 = group[0]
        base = MergedRecommendation(
            title=first.title.strip(),
            rationale=first.rationale.strip(),
            sources=[role0],
            impact_estimate=first.impact_estimate,
            effort=first.effort,
            priority=first.priority,
            see_also=[],
            source_confidence=conf0,
        )
        max_conf = conf0
        for rec, role, conf in group[1:]:
            max_conf = max(max_conf, conf)
            base = _merge_two_recs(base, rec, role, rec.title.strip())
        merged.append(base.model_copy(update={"source_confidence": max_conf}))

    merged.sort(key=_rec_sort_key, reverse=True)

    executive_bullets = [f"**{f.source_role}**: {f.headline.strip()}" for f in findings]

    return MergedReport(
        findings=findings,
        merged_recommendations=merged,
        metric_rollup=metric_rollup,
        executive_bullets=executive_bullets,
    )
