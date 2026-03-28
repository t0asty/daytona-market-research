from __future__ import annotations

import re
from typing import Any

from report_gen.models import AgentFinding, Recommendation

from workers.social_public.finding import build_organic_social_finding


def _channel_label(channel_url: str) -> str:
    m = re.search(r"@([^/?#]+)", channel_url)
    if m:
        return f"@{m.group(1)}"
    m = re.search(r"channel/([^/?#]+)", channel_url)
    if m:
        return f"channel:{m.group(1)[:12]}"
    return "channel"


def mock_youtube_finding(channel_url: str, *, max_items: int = 10) -> AgentFinding:
    """
    Build an ``AgentFinding`` with **synthetic** video rows (no network).

    For sandboxes or tiers that cannot reach youtube.com; clearly labeled in
    ``headline``, ``evidence``, ``raw_notes``, and low ``confidence``.
    """
    label = _channel_label(channel_url)
    n = max(1, min(max_items, 25))
    videos: list[dict[str, Any]] = []
    for i in range(n):
        views_k = (i + 1) * 87 + 12
        videos.append(
            {
                "title": f"[MOCK] {label} — sample short {i + 1}",
                "url": f"https://www.youtube.com/watch?v=mock{i + 1:06d}",
                "views_text": f"{views_k}K views",
            }
        )

    base = build_organic_social_finding(
        channel_url=channel_url,
        videos=videos,
        agent_id="mock-youtube",
        partial=False,
    )

    evidence = [
        "MOCK DATA — not fetched from YouTube; for demos when outbound access to youtube.com is blocked.",
        *base.evidence,
    ]
    recs = [
        Recommendation(
            title="Swap mock for live scrape when egress allows",
            rationale="Replace `--mock` / SOCIAL_YOUTUBE_MOCK with Playwright against the real channel "
            "or use the YouTube Data API once network policy permits.",
            impact_estimate="high",
            effort="medium",
            priority=60,
        )
    ]

    raw = (
        base.raw_notes or ""
    ) + "\n\nSynthetic metrics for pipeline testing. Do not use for real decisions."
    return base.model_copy(
        update={
            "headline": f"MOCK: {n} simulated public videos for {label} (no YouTube network).",
            "confidence": 0.25,
            "recommendations": recs,
            "evidence": evidence,
            "raw_notes": raw.strip(),
        }
    )
