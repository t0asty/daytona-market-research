from __future__ import annotations

import json

from report_gen.models import MergedReport


SYSTEM_PROMPT = """You are an editor for marketing performance reports.
You receive structured JSON that already contains all numbers and facts.
Rewrite **only** the executive summary as concise Markdown bullet points (use `- ` lines).
Do not introduce new metrics, percentages, dollar amounts, or dates that are not already implied by the input.
Do not name tools or models. Keep a professional analyst tone."""


def polish_executive_summary(merged: MergedReport, *, model: str = "gpt-4o-mini") -> str:
    """Single LLM call: polished executive bullets from merged JSON. Requires `openai` extra."""
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
        + "\n```\n\nReturn only the executive summary bullets in Markdown."
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
        raise RuntimeError("LLM returned an empty executive summary")
    return text
