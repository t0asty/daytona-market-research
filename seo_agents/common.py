"""Shared utilities for SEO agent scripts.

All scripts run inside Daytona sandboxes and output AgentFinding JSON to stdout.
"""

import json
import random
import sys
import time
from datetime import datetime, timezone
from typing import Any

# User agents for web scraping — rotate to avoid blocks
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
]


def get_random_ua() -> str:
    return random.choice(USER_AGENTS)


def get_headers() -> dict[str, str]:
    return {
        "User-Agent": get_random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def rate_limit(min_delay: float = 1.0, max_delay: float = 3.0) -> None:
    """Sleep for a random interval to avoid rate limiting."""
    time.sleep(random.uniform(min_delay, max_delay))


def retry_request(func, max_retries: int = 3, backoff: float = 2.0):
    """Retry a function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as exc:
            if attempt == max_retries - 1:
                raise
            wait = backoff * (2 ** attempt)
            print(f"Retry {attempt + 1}/{max_retries} after {wait}s: {exc}", file=sys.stderr)
            time.sleep(wait)


def load_input() -> dict[str, Any]:
    """Load input configuration from input.json."""
    with open("input.json") as f:
        return json.load(f)


def build_finding(
    source_role: str,
    headline: str,
    metrics: list[dict] | None = None,
    recommendations: list[dict] | None = None,
    evidence: list[str] | None = None,
    confidence: float = 0.7,
    raw_notes: str | None = None,
    extra: dict | None = None,
) -> dict[str, Any]:
    """Build an AgentFinding dict matching the dashboard schema.

    Args:
        source_role: Agent identifier (e.g. "keyword_research").
        headline: One-line takeaway.
        metrics: List of {name, value, unit?, delta?, benchmark?}.
        recommendations: List of {title, rationale, impact_estimate?, effort?, priority?}.
        evidence: List of citation/evidence strings.
        confidence: 0.0-1.0 confidence score.
        raw_notes: Optional longer text for collapsible block.
        extra: Additional fields to include (e.g. _keywords for inter-stage data).

    Returns:
        Dict matching the AgentFinding schema.
    """
    now = datetime.now(timezone.utc)
    quarter = (now.month - 1) // 3 + 1
    finding: dict[str, Any] = {
        "schema_version": 1,
        "source_role": source_role,
        "period": f"{now.year}-Q{quarter}",
        "as_of": now.strftime("%Y-%m-%d"),
        "headline": headline,
        "metrics": metrics or [],
        "recommendations": recommendations or [],
        "evidence": evidence or [],
        "confidence": confidence,
        "raw_notes": raw_notes,
    }
    if extra:
        finding.update(extra)
    return finding


def output_finding(finding: dict[str, Any]) -> None:
    """Print the AgentFinding JSON to stdout for the orchestrator to capture."""
    print(json.dumps(finding, indent=2))
