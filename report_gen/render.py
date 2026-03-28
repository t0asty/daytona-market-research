from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from report_gen.models import MergedReport


def _templates_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def render_report(
    merged: MergedReport,
    *,
    executive_summary_md: str | None = None,
) -> str:
    """
    Render full markdown report from merged findings.
    If executive_summary_md is set (e.g. from LLM), it replaces the template block.
    """
    env = Environment(
        loader=FileSystemLoader(_templates_dir()),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tpl = env.get_template("report.md.j2")
    return tpl.render(
        merged=merged,
        executive_summary_md=executive_summary_md,
    )
