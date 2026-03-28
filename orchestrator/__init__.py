"""Modular marketing-research agents and an orchestrator entrypoint.

Each agent produces one ``AgentFinding`` JSON document (see ``report_gen.models``).
Sandbox execution uses **mock** data only so Daytona tiers without reliable egress still run end-to-end.

Daytona **MCP** in Cursor is for interactive control; automated orchestration uses the **Daytona Python SDK**
(see ``orchestrator.remote_daytona``), same family of API as ``report_gen.daytona_runner``.
"""

from orchestrator.context import ResearchContext
from orchestrator.registry import AGENTS, AgentSpec, get_agent, list_agent_specs, run_registered

__all__ = [
    "AGENTS",
    "AgentSpec",
    "ResearchContext",
    "get_agent",
    "list_agent_specs",
    "run_registered",
]
