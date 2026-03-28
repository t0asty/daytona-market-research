from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from report_gen.models import AgentFinding, Metric, Recommendation


def _parse_view_text(views_text: str) -> tuple[str | int | float, str | None]:
    """
    Normalize YouTube-style view strings to a numeric value when unambiguous.
    Keeps original string as value when parsing fails.
    """
    raw = views_text.strip()
    lower = raw.lower()
    if "no views" in lower or raw == "":
        return 0, "count"
    # Strip "views" / "view" suffix noise
    for suffix in (" views", " view"):
        if lower.endswith(suffix):
            raw = raw[: -len(suffix)].strip()
            lower = raw.lower()
            break
    mult = 1.0
    if lower.endswith("k"):
        mult = 1_000.0
        raw = raw[:-1].strip()
    elif lower.endswith("m"):
        mult = 1_000_000.0
        raw = raw[:-1].strip()
    elif lower.endswith("b"):
        mult = 1_000_000_000.0
        raw = raw[:-1].strip()
    cleaned = raw.replace(",", "").replace("·", "").strip()
    try:
        return int(float(cleaned) * mult), "count"
    except ValueError:
        return views_text, None


def build_organic_social_finding(
    *,
    channel_url: str,
    videos: list[dict[str, Any]],
    headline: str | None = None,
    agent_id: str | None = None,
    partial: bool = False,
) -> AgentFinding:
    """
    Build an ``AgentFinding`` from scraped rows.

    Each row may contain: title (str), url (str), views_text (str).
    """
    as_of = datetime.now(UTC).strftime("%Y-%m-%d")
    metrics: list[Metric] = []
    evidence: list[str] = [f"Source channel/list URL: {channel_url}"]

    total_views_numeric = 0.0
    numeric_count = 0
    for row in videos:
        title = str(row.get("title", "")).strip()
        url = str(row.get("url", "")).strip()
        views_text = str(row.get("views_text", "")).strip()
        if not title and not url:
            continue
        idx = len(metrics) + 1
        label = f"Video {idx} views"
        val, _unit = _parse_view_text(views_text) if views_text else (views_text, None)
        if isinstance(val, int | float):
            total_views_numeric += float(val)
            numeric_count += 1
        metrics.append(
            Metric(
                name=label,
                value=val,
                unit="views" if isinstance(val, int | float) else None,
            )
        )
        line_bits = [b for b in (title, url, views_text) if b]
        evidence.append(" — ".join(line_bits))

    if numeric_count:
        metrics.insert(
            0,
            Metric(
                name="Sum of parsed video views (sample)",
                value=int(total_views_numeric)
                if total_views_numeric == int(total_views_numeric)
                else round(total_views_numeric, 2),
                unit="views",
            ),
        )

    if headline is None:
        n = len([v for v in videos if str(v.get("title", "")).strip()])
        headline = (
            f"Sampled {n} public videos from the channel list; see per-video view metrics."
            if n
            else "No videos extracted from the channel page (layout or access may have blocked parsing)."
        )

    confidence = 0.45 if partial or not videos else 0.72
    if not videos:
        confidence = 0.2

    recs: list[Recommendation] = []
    if partial or not videos:
        recs.append(
            Recommendation(
                title="Validate selectors or try agent mode",
                rationale="YouTube DOM changes, consent interstitials, or geo blocks can empty extraction; "
                "re-run with updated selectors or `social-youtube-worker --mode agent` if configured.",
                impact_estimate="medium",
                effort="low",
                priority=50,
            )
        )

    return AgentFinding(
        schema_version=1,
        agent_id=agent_id,
        source_role="organic_social",
        period=None,
        as_of=as_of,
        headline=headline,
        metrics=metrics,
        recommendations=recs,
        evidence=evidence,
        confidence=confidence,
        raw_notes="Public page scrape only; not a substitute for platform APIs or authenticated analytics.",
    )
