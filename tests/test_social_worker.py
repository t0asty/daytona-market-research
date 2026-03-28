from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from report_gen.models import AgentFinding
from workers.social_public.browser_use_runner import _extract_json_object
from workers.social_public.finding import build_organic_social_finding


def test_build_organic_social_finding_sums_views() -> None:
    rows = [
        {"title": "A", "url": "https://www.youtube.com/watch?v=1", "views_text": "1.2M views"},
        {"title": "B", "url": "https://www.youtube.com/watch?v=2", "views_text": "500K views"},
    ]
    f = build_organic_social_finding(
        channel_url="https://www.youtube.com/@x/videos",
        videos=rows,
        agent_id="test",
        partial=False,
    )
    assert f.source_role == "organic_social"
    assert f.metrics[0].name == "Sum of parsed video views (sample)"
    assert f.metrics[0].value == 1_700_000
    names = [m.name for m in f.metrics]
    assert "Video 1 views" in names


def test_build_organic_social_finding_empty_partial() -> None:
    f = build_organic_social_finding(
        channel_url="https://www.youtube.com/@x/videos",
        videos=[],
        partial=True,
    )
    assert f.confidence < 0.5
    assert f.recommendations


def test_organic_social_youtube_fixture_validates() -> None:
    raw = json.loads(
        Path("examples/fixtures/organic_social_youtube.finding.json").read_text(encoding="utf-8")
    )
    AgentFinding.model_validate(raw)


def test_extract_json_object() -> None:
    assert _extract_json_object('{"videos":[]}') == {"videos": []}
    assert _extract_json_object('prefix {"a": 1} suffix') == {"a": 1}


def test_daytona_merge_report_cli(tmp_path: Path) -> None:
    import subprocess
    import sys

    extra = tmp_path / "sandbox.finding.json"
    extra.write_text(
        Path("examples/fixtures/organic_social_youtube.finding.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    out_md = tmp_path / "merged.md"
    repo_root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "workers.social_public.handoff",
            str(extra),
            "--fixtures-glob",
            "examples/fixtures/funnel.finding.json",
            "--out",
            str(out_md),
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert out_md.is_file()
    body = out_md.read_text(encoding="utf-8")
    assert "sampled 2 public videos" in body.lower()


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("RUN_YOUTUBE_INTEGRATION"),
    reason="Set RUN_YOUTUBE_INTEGRATION=1 to run live YouTube scrape (network + Chromium).",
)
def test_youtube_playwright_smoke() -> None:
    """Live YouTube fetch; requires playwright, Chromium, and outbound HTTPS."""
    from workers.social_public.youtube_playwright import scrape_youtube_video_rows

    url = "https://www.youtube.com/@YouTube/videos"
    result = scrape_youtube_video_rows(url, max_items=3)
    assert isinstance(result.videos, list)
    # YouTube may block datacenter IPs; allow empty with partial flag
    if not result.videos:
        pytest.skip("No rows returned (geo/block); partial=%s err=%s" % (result.partial, result.error))
