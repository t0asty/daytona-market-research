from __future__ import annotations

from report_gen.models import AgentFinding

from orchestrator.context import ResearchContext
from workers.mock_agents.saas_b2b import mock_organic_search_finding


def run(ctx: ResearchContext) -> AgentFinding:
    return mock_organic_search_finding(company=ctx.company)
