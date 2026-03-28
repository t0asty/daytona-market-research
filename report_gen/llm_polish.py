from __future__ import annotations

import json

from report_gen.models import MergedReport


SYSTEM_PROMPT = """You are an editor for marketing performance reports.
You receive structured JSON that already contains all numbers and facts.

Write **only** the opening summary for Part 1 of the report, for a busy non-expert reader
(e.g. a CEO). Use plain language; briefly explain jargon on first use if unavoidable.

Structure (Markdown):
1. One short paragraph (2–4 sentences) — the "bottom line".
2. Then 3–6 bullet lines starting with `- ` — concrete, actionable takeaways (what to do or decide), not channel jargon.

Do not introduce new metrics, percentages, dollar amounts, or dates that are not already in the input.
Do not name tools or models. Keep a calm, professional tone."""


def polish_executive_summary(merged: MergedReport, *, model: str = "gpt-4o-mini") -> str:
    """Single LLM call: Part 1 non-expert summary from merged JSON. Requires `openai` extra."""
    try:
        from openai import OpenAI
    except ImportError as e:
        raise ImportError(
            "Install the LLM extra: pip install '.[llm]' (adds openai)"
        ) from e

    client = OpenAI()
    payload = merged.model_dump(mode="json")
    user_content = (
        "Merged report JSON (authoritative facts):\n```json\n"
        + json.dumps(payload, indent=2)
        + "\n```\n\nReturn only the Part 1 summary Markdown (paragraph + bullets), no heading."
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
    )
    text = (resp.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("LLM returned an empty Part 1 summary")
    return text
