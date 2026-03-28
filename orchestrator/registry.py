from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from report_gen.models import AgentFinding

from orchestrator.context import ResearchContext


@dataclass(frozen=True)
class AgentSpec:
    """One pluggable research agent the orchestrator can run (local or in a Daytona sandbox)."""

    id: str
    title: str
    source_role: str
    description: str
    run: Callable[[ResearchContext], AgentFinding]


def _build_agents() -> dict[str, AgentSpec]:
    from orchestrator.agents import (
        funnel,
        google_ads,
        google_maps,
        g2_review_sites,
        linkedin,
        meta_ads,
        organic_search,
        youtube,
    )

    specs: list[AgentSpec] = [
        AgentSpec(
            id="youtube",
            title="YouTube public channel",
            source_role="organic_social",
            description="Mock public video list and view metrics (no YouTube network).",
            run=youtube.run,
        ),
        AgentSpec(
            id="google_ads",
            title="Google Ads / paid search",
            source_role="paid_search",
            description="Mock paid search performance and impression share narrative.",
            run=google_ads.run,
        ),
        AgentSpec(
            id="organic_search",
            title="Organic search / SEO surface",
            source_role="organic_search",
            description="Mock Search Console-style organic trends and content gaps.",
            run=organic_search.run,
        ),
        AgentSpec(
            id="funnel",
            title="PLG funnel & conversion",
            source_role="funnel",
            description="Mock signup → activation → trial conversion story.",
            run=funnel.run,
        ),
        AgentSpec(
            id="google_maps",
            title="Google Maps / local pack",
            source_role="google_maps",
            description="Mock local finder rankings, reviews, and map-pack visibility.",
            run=google_maps.run,
        ),
        AgentSpec(
            id="linkedin",
            title="LinkedIn company presence",
            source_role="linkedin_organic",
            description="Mock follower growth, post reach, and employee advocacy signals.",
            run=linkedin.run,
        ),
        AgentSpec(
            id="meta_ads",
            title="Meta Ads Library (competitive)",
            source_role="meta_ads",
            description="Mock active creative themes, spend bands, and audience overlap hints.",
            run=meta_ads.run,
        ),
        AgentSpec(
            id="review_sites",
            title="G2 / Capterra / peer reviews",
            source_role="review_aggregators",
            description="Mock B2B review scores, category placement, and sentiment drivers.",
            run=g2_review_sites.run,
        ),
    ]
    return {s.id: s for s in specs}


AGENTS: dict[str, AgentSpec] = _build_agents()


def list_agent_specs() -> list[AgentSpec]:
    return sorted(AGENTS.values(), key=lambda s: s.id)


def get_agent(agent_id: str) -> AgentSpec:
    spec = AGENTS.get(agent_id)
    if spec is None:
        known = ", ".join(sorted(AGENTS))
        raise KeyError(f"Unknown agent id {agent_id!r}. Known: {known}")
    return spec


def run_registered(agent_id: str, ctx: ResearchContext) -> AgentFinding:
    return get_agent(agent_id).run(ctx)
