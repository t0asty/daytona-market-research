from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

MetricValue = str | int | float

ImpactLevel = Literal["high", "medium", "low"]
EffortLevel = Literal["high", "medium", "low"]


class Metric(BaseModel):
    """A single KPI or statistic from an agent."""

    name: str
    value: MetricValue
    unit: str | None = None
    delta: MetricValue | None = None
    benchmark: str | None = None


class Recommendation(BaseModel):
    """Actionable item from an agent."""

    title: str
    rationale: str
    impact_estimate: ImpactLevel | None = None
    effort: EffortLevel | None = None
    priority: int | None = Field(
        default=None,
        description="Higher means more important when merging and sorting.",
    )


class AgentFinding(BaseModel):
    """
    One JSON document per agent. Producers (sandboxes, scripts) must match this shape.
    """

    schema_version: int = 1
    agent_id: str | None = None
    source_role: str
    period: str | None = None
    as_of: str | None = None
    headline: str
    metrics: list[Metric] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    raw_notes: str | None = None

    @field_validator("source_role")
    @classmethod
    def strip_role(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("source_role must be non-empty")
        return s


class MergedRecommendation(BaseModel):
    """Recommendation after cross-agent deduplication."""

    title: str
    rationale: str
    sources: list[str]
    impact_estimate: ImpactLevel | None = None
    effort: EffortLevel | None = None
    priority: int | None = None
    see_also: list[str] = Field(default_factory=list)
    source_confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Max confidence among agents that contributed to this row.",
    )


class MetricRollupRow(BaseModel):
    """Same metric name shown per channel/agent — no cross-role arithmetic."""

    name: str
    unit: str | None = None
    by_role: dict[str, MetricValue]
    delta_by_role: dict[str, MetricValue] = Field(default_factory=dict)


class MergedReport(BaseModel):
    """Deterministic merge output before rendering."""

    findings: list[AgentFinding]
    merged_recommendations: list[MergedRecommendation]
    metric_rollup: list[MetricRollupRow]
    executive_bullets: list[str]
