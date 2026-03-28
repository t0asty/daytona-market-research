from __future__ import annotations

from report_gen.models import AgentFinding

from workers.mock_agents.saas_b2b import (
    mock_funnel_plg_finding,
    mock_organic_search_finding,
    mock_paid_search_finding,
)


def test_mock_paid_search_validates() -> None:
    f = mock_paid_search_finding(company="Orbital")
    AgentFinding.model_validate(f.model_dump(mode="json"))
    assert f.source_role == "paid_search"
    assert f.agent_id == "mock-paid-search"
    assert f.confidence < 0.5
    assert any("MOCK" in e.upper() for e in f.evidence)


def test_mock_organic_search_validates() -> None:
    f = mock_organic_search_finding(company="Nimbus")
    AgentFinding.model_validate(f.model_dump(mode="json"))
    assert f.source_role == "organic_search"


def test_mock_funnel_plg_validates() -> None:
    f = mock_funnel_plg_finding(company="Stacklane")
    AgentFinding.model_validate(f.model_dump(mode="json"))
    assert f.source_role == "funnel"
    assert any(m.name == "Net revenue retention (mock)" for m in f.metrics)
