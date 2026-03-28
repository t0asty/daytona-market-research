from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from report_gen.models import MergedReport


def _templates_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def humanize_role(role: str) -> str:
    """Turn `paid_social` into `Paid social` for non-technical readers."""
    return str(role).replace("_", " ").replace("-", " ").strip().title()


def executive_bullet_humanize(line: str) -> str:
    """
    Format `**source_role**: headline` with a humanized role label.
    Falls back to the original line if the pattern does not match.
    """
    m = re.match(r"^\*\*([^*]+)\*\*:\s*(.*)$", line.strip(), flags=re.DOTALL)
    if not m:
        return line
    raw_role, rest = m.group(1).strip(), m.group(2).strip()
    return f"**{humanize_role(raw_role)}**: {rest}"


def render_report(
    merged: MergedReport,
    *,
    executive_summary_md: str | None = None,
) -> str:
    """
    Render full markdown report from merged findings.
    If executive_summary_md is set (e.g. from LLM), it replaces the default
    channel-headline bullets in Part 1 (summary subsection only).
    """
    env = Environment(
        loader=FileSystemLoader(_templates_dir()),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["humanize_role"] = humanize_role
    env.filters["executive_bullet_humanize"] = executive_bullet_humanize
    tpl = env.get_template("report.md.j2")
    return tpl.render(
        merged=merged,
        executive_summary_md=executive_summary_md,
    )
