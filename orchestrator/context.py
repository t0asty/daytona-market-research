from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class ResearchContext:
    """Inputs shared across marketing research agents (all mocks use this shape)."""

    company: str = "Acme"
    domain: str = ""
    locale: str = "en-US"
    max_items: int = 10
    youtube_channel_url: str | None = None

    def company_slug(self) -> str:
        s = re.sub(r"[^a-z0-9]+", "-", self.company.lower()).strip("-")
        return s or "company"

    def default_youtube_channel_url(self) -> str:
        return f"https://www.youtube.com/@{self.company_slug()}/videos"

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> ResearchContext:
        return cls(
            company=str(data.get("company") or "Acme"),
            domain=str(data.get("domain") or ""),
            locale=str(data.get("locale") or "en-US"),
            max_items=int(data.get("max_items") or 10),
            youtube_channel_url=data.get("youtube_channel_url"),
        )

    @classmethod
    def load_json_file(cls, path: Path) -> ResearchContext:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Context JSON must be an object")
        return cls.from_json_dict(raw)
