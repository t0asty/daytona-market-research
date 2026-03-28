from __future__ import annotations

from report_gen.models import AgentFinding

from orchestrator.context import ResearchContext
from workers.social_public.mock_youtube import mock_youtube_finding


def run(ctx: ResearchContext) -> AgentFinding:
    url = ctx.youtube_channel_url or ctx.default_youtube_channel_url()
    return mock_youtube_finding(url, max_items=ctx.max_items)
