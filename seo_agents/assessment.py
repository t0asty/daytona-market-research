"""Assessment Agent — compiles and evaluates all SEO research findings.

Input (input.json):
    domain: str — target domain
    findings: dict[str, AgentFinding] — all prior stage findings keyed by source_role

Output: AgentFinding JSON to stdout (executive summary with merged recommendations)
"""

from collections import defaultdict

from common import build_finding, load_input, output_finding


def normalize_title(title: str) -> str:
    """Normalize recommendation title for dedup comparison."""
    return " ".join(title.lower().split())


def main():
    config = load_input()
    domain = config["domain"]
    findings = config.get("findings", {})

    if not findings:
        output_finding(build_finding(
            source_role="seo_assessment",
            headline=f"No findings to assess for {domain}",
            confidence=0.1,
        ))
        return

    # Collect all recommendations across agents
    all_recs = []
    for source_role, finding in findings.items():
        for rec in finding.get("recommendations", []):
            all_recs.append({
                **rec,
                "_source": source_role,
                "_confidence": finding.get("confidence", 0.5),
            })

    # Deduplicate recommendations by normalized title
    merged_recs: dict[str, dict] = {}
    for rec in all_recs:
        key = normalize_title(rec.get("title", ""))
        if key in merged_recs:
            existing = merged_recs[key]
            # Merge: keep highest priority, combine rationale
            existing["_sources"].append(rec["_source"])
            if (rec.get("priority") or 0) > (existing.get("priority") or 0):
                existing["priority"] = rec["priority"]
            if rec.get("rationale") and rec["rationale"] not in existing.get("rationale", ""):
                existing["rationale"] += f" | {rec['_source']}: {rec['rationale']}"
            existing["_max_confidence"] = max(existing["_max_confidence"], rec.get("_confidence", 0.5))
        else:
            merged_recs[key] = {
                **rec,
                "_sources": [rec["_source"]],
                "_max_confidence": rec.get("_confidence", 0.5),
            }

    # Sort by priority (desc), then by number of sources
    sorted_recs = sorted(
        merged_recs.values(),
        key=lambda r: (r.get("priority", 0), len(r.get("_sources", []))),
        reverse=True,
    )

    # Top 5 priority actions
    top_recs = []
    for rec in sorted_recs[:7]:
        clean_rec = {
            "title": rec["title"],
            "rationale": rec.get("rationale", ""),
            "impact_estimate": rec.get("impact_estimate"),
            "effort": rec.get("effort"),
            "priority": rec.get("priority"),
        }
        top_recs.append(clean_rec)

    # Aggregate metrics
    aggregate_metrics = []
    # Collect key metrics from each finding
    for source_role, finding in findings.items():
        for metric in finding.get("metrics", []):
            aggregate_metrics.append({
                "name": f"{source_role}: {metric['name']}",
                "value": metric["value"],
                "unit": metric.get("unit"),
            })

    # Build executive bullets
    executive_bullets = []
    for source_role, finding in findings.items():
        headline = finding.get("headline", "")
        if headline:
            executive_bullets.append(f"**{source_role}**: {headline}")

    # Compute weighted confidence
    confidences = [f.get("confidence", 0.5) for f in findings.values()]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

    # Summary stats
    total_recs = len(all_recs)
    high_impact = sum(1 for r in all_recs if r.get("impact_estimate") == "high")
    agents_completed = len(findings)

    headline_parts = []
    headline_parts.append(f"{agents_completed} agents completed")
    headline_parts.append(f"{total_recs} recommendations")
    headline_parts.append(f"{high_impact} high-impact")
    headline = f"SEO assessment for {domain}: {'; '.join(headline_parts)}"

    finding = build_finding(
        source_role="seo_assessment",
        headline=headline,
        metrics=[
            {"name": "Agents completed", "value": agents_completed},
            {"name": "Total recommendations", "value": total_recs},
            {"name": "High-impact recommendations", "value": high_impact},
            {"name": "Unique recommendations (after merge)", "value": len(merged_recs)},
        ] + aggregate_metrics[:10],  # Include top agent metrics
        recommendations=top_recs,
        evidence=executive_bullets,
        confidence=round(avg_confidence, 2),
        raw_notes="\n\n".join(
            f"## {role}\n{finding.get('headline', 'No headline')}\n"
            f"Confidence: {finding.get('confidence', 'N/A')}\n"
            f"Recommendations: {len(finding.get('recommendations', []))}"
            for role, finding in findings.items()
        ),
    )

    output_finding(finding)


if __name__ == "__main__":
    main()
