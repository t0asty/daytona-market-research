from __future__ import annotations

import markdown
from markdown.extensions.tables import TableExtension


def markdown_to_html_document(md: str, *, title: str = "Marketing report") -> str:
    body = markdown.markdown(
        md,
        extensions=["fenced_code", "nl2br", TableExtension()],
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
  <style>
    @page {{ size: A4; margin: 18mm 16mm; }}
    body {{
      font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
      font-size: 10.5pt;
      line-height: 1.45;
      color: #1a1a1a;
      max-width: 100%;
    }}
    h1 {{ font-size: 18pt; margin: 0 0 0.6em; font-weight: 700; letter-spacing: -0.02em; }}
    h2 {{ font-size: 13pt; margin: 1.2em 0 0.5em; border-bottom: 1px solid #e5e5e5; padding-bottom: 0.25em; }}
    h3 {{ font-size: 11pt; margin: 1em 0 0.4em; color: #333; }}
    p {{ margin: 0.5em 0; }}
    ul, ol {{ margin: 0.4em 0 0.6em 1.2em; padding: 0; }}
    li {{ margin: 0.2em 0; }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 0.6em 0 1em;
      font-size: 9.5pt;
    }}
    th, td {{
      border: 1px solid #d4d4d4;
      padding: 6px 8px;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: #f4f4f5; font-weight: 600; }}
    tr:nth-child(even) td {{ background: #fafafa; }}
    code {{ font-family: ui-monospace, monospace; font-size: 0.9em; background: #f4f4f5; padding: 0.1em 0.35em; border-radius: 3px; }}
    pre {{ background: #f4f4f5; padding: 0.75em; border-radius: 6px; overflow-x: auto; font-size: 9pt; }}
    details {{ margin: 0.5em 0; padding: 0.5em 0.75em; border: 1px solid #e5e5e5; border-radius: 6px; background: #fafafa; }}
    summary {{ font-weight: 600; cursor: pointer; }}
    hr {{ border: none; border-top: 1px solid #e5e5e5; margin: 1.2em 0; }}
    em {{ color: #444; }}
    strong {{ font-weight: 600; }}
  </style>
</head>
<body>
{body}
</body>
</html>"""


def render_pdf_bytes(html: str) -> bytes:
    """Render HTML to PDF using Playwright (Chromium)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise ImportError(
            "PDF export requires Playwright. Install: pip install '.[web]' && playwright install chromium"
        ) from e

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            pdf = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "16mm", "right": "14mm", "bottom": "16mm", "left": "14mm"},
            )
        finally:
            browser.close()
    return pdf
