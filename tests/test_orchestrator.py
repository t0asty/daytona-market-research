from __future__ import annotations

import argparse
import json

import pytest

from orchestrator import cli as orchestrator_cli
from orchestrator.context import ResearchContext
from orchestrator.registry import AGENTS, list_agent_specs, run_registered
from orchestrator.uploads import minimal_python_relative_paths, validate_minimal_tree


def test_registry_covers_expected_channels() -> None:
    ids = {s.id for s in list_agent_specs()}
    assert "youtube" in ids
    assert "google_ads" in ids
    assert "google_maps" in ids
    assert "linkedin" in ids
    assert "meta_ads" in ids
    assert "review_sites" in ids


@pytest.mark.parametrize("agent_id", sorted(AGENTS))
def test_each_agent_returns_valid_finding(agent_id: str) -> None:
    ctx = ResearchContext(company="TestCo", domain="testco.example", max_items=3)
    finding = run_registered(agent_id, ctx)
    raw = finding.model_dump()
    assert raw["headline"]
    assert raw["source_role"]
    assert isinstance(raw["metrics"], list)


def test_context_json_roundtrip(tmp_path) -> None:
    p = tmp_path / "ctx.json"
    p.write_text(
        json.dumps(
            {
                "company": "Co",
                "domain": "co.test",
                "locale": "de-DE",
                "max_items": 5,
                "youtube_channel_url": "https://www.youtube.com/@co/videos",
            }
        ),
        encoding="utf-8",
    )
    ctx = ResearchContext.load_json_file(p)
    assert ctx.company == "Co"
    assert ctx.max_items == 5
    assert ctx.youtube_channel_url is not None


def test_minimal_upload_bundle_exists() -> None:
    validate_minimal_tree()
    paths = minimal_python_relative_paths()
    assert any(p.endswith("orchestrator/cli.py") for p in paths)
    assert "report_gen/models.py" in paths


def test_doctor_exits_zero(capsys) -> None:
    assert orchestrator_cli.cmd_doctor(argparse.Namespace()) == 0
    out = capsys.readouterr().out
    assert "DAYTONA_API_KEY" in out
    assert "OPENAI_API_KEY" in out
