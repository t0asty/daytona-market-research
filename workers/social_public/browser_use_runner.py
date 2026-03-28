from __future__ import annotations

import json
import os
import re
from typing import Any

from report_gen.models import AgentFinding

from workers.social_public.finding import build_organic_social_finding


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort parse of a JSON object from model/browser-use output."""
    text = text.strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


async def run_browser_use_youtube_sample(
    channel_videos_url: str,
    *,
    max_items: int = 10,
) -> AgentFinding:
    """
    LLM-driven extraction via browser-use. Requires ``pip install '.[browser-agent]'`` and LLM keys.

    Network allowlisting should still be enforced by Daytona; prompts reinforce staying on-page.
    """
    try:
        from browser_use import Agent, Browser
        from langchain_openai import ChatOpenAI
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "browser-use path requires optional deps: pip install -e '.[browser-agent]'"
        ) from exc

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY must be set for browser-use + ChatOpenAI.")

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=model)
    browser = Browser()
    task = (
        f"Navigate to {channel_videos_url}. Stay on youtube.com only. "
        f"Wait until video titles are visible. Extract up to {max_items} videos from the listing. "
        "For each item capture: title (string), views_text exactly as shown (e.g. '1.2M views'), "
        "and url (full https URL to the watch page if available). "
        "When finished, reply with ONLY a compact JSON object, no markdown fences, "
        'with shape: {{"videos":[{{"title":"...","views_text":"...","url":"..."}}]}}. '
        "Use only text visible on the page; if a field is missing use an empty string."
    )
    agent = Agent(task=task, llm=llm, browser=browser)
    history = await agent.run()

    text_out = history.final_result() or ""
    if not text_out.strip() and getattr(history, "extracted_content", None):
        chunks = [c for c in history.extracted_content if c]
        text_out = "\n".join(str(c) for c in chunks)
    if not text_out.strip():
        text_out = str(history)

    data = _extract_json_object(text_out)
    videos: list[dict[str, Any]] = []
    if data and isinstance(data.get("videos"), list):
        for row in data["videos"][:max_items]:
            if isinstance(row, dict):
                videos.append(
                    {
                        "title": str(row.get("title", "")),
                        "views_text": str(row.get("views_text", "")),
                        "url": str(row.get("url", "")),
                    }
                )

    partial = not videos
    finding = build_organic_social_finding(
        channel_url=channel_videos_url,
        videos=videos,
        headline="Browser-use agent sampled public YouTube listing metrics."
        if videos
        else "Browser-use agent returned no structured videos; see raw_notes.",
        agent_id="browser-use",
        partial=partial,
    )
    notes = finding.raw_notes or ""
    if text_out:
        notes = (notes + "\n\nAgent output (truncated):\n" + text_out[:4000]).strip()
    return finding.model_copy(update={"raw_notes": notes})
