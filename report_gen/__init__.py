"""Merge structured agent findings into marketing performance reports."""

from report_gen.merge import merge_findings
from report_gen.models import AgentFinding, MergedReport, Metric, Recommendation

__all__ = [
    "AgentFinding",
    "MergedReport",
    "Metric",
    "Recommendation",
    "merge_findings",
]
