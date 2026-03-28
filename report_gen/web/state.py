from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class ReportState:
    """In-memory latest run (hackathon / single-tenant demo)."""

    lock: Lock = field(default_factory=Lock)
    ready: bool = False
    running: bool = False
    markdown: str = ""
    error: str | None = None


state = ReportState()
