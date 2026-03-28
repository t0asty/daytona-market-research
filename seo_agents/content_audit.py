"""Content Audit Agent — crawls and audits site content quality.

Input (input.json):
    domain: str — target domain
    max_pages: int — max pages to crawl (default 20)

Output: AgentFinding JSON to stdout
"""

import sys
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup
from common import (
    build_finding,
    get_headers,
    load_input,
    output_finding,
    rate_limit,
    retry_request,
)


def fetch_sitemap_urls(domain: str, max_urls: int = 20) -> list[str]:
    """Try to find and parse sitemap.xml for page URLs."""
    urls = []
    sitemap_locations = [
        f"https://{domain}/sitemap.xml",
        f"https://{domain}/sitemap_index.xml",
        f"https://www.{domain}/sitemap.xml",
    ]

    for sitemap_url in sitemap_locations:
        try:
            resp = requests.get(sitemap_url, headers=get_headers(), timeout=10)
            if resp.status_code != 200:
                continue

            root = ElementTree.fromstring(resp.content)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Check for sitemap index
            for sitemap in root.findall(".//sm:sitemap/sm:loc", ns):
                if len(urls) >= max_urls:
                    break
                try:
                    sub_resp = requests.get(sitemap.text, headers=get_headers(), timeout=10)
                    sub_root = ElementTree.fromstring(sub_resp.content)
                    for url_elem in sub_root.findall(".//sm:url/sm:loc", ns):
                        urls.append(url_elem.text)
                        if len(urls) >= max_urls:
                            break
                except Exception:
                    pass
                rate_limit(0.5, 1.0)

            # Direct URL entries
            for url_elem in root.findall(".//sm:url/sm:loc", ns):
                urls.append(url_elem.text)
                if len(urls) >= max_urls:
                    break

            if urls:
                return urls[:max_urls]
        except Exception as exc:
            print(f"Sitemap fetch failed for {sitemap_url}: {exc}", file=sys.stderr)

    # Fallback: just use homepage
    return [f"https://{domain}/"]


def audit_page(url: str) -> dict:
    """Audit a single page for SEO content quality."""
    issues = []
    try:
        resp = retry_request(
            lambda: requests.get(url, headers=get_headers(), timeout=15, allow_redirects=True)
        )
        if resp.status_code != 200:
            return {"url": url, "status": resp.status_code, "issues": [f"HTTP {resp.status_code}"], "word_count": 0}

        soup = BeautifulSoup(resp.text, "lxml")

        # Title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""
        if not title:
            issues.append("missing_title")
        elif len(title) > 60:
            issues.append("title_too_long")
        elif len(title) < 20:
            issues.append("title_too_short")

        # Meta description
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "")
        if not meta_desc:
            issues.append("missing_meta_description")
        elif len(meta_desc) > 160:
            issues.append("meta_description_too_long")

        # H1
        h1_tags = soup.find_all("h1")
        if not h1_tags:
            issues.append("missing_h1")
        elif len(h1_tags) > 1:
            issues.append("multiple_h1")

        # Content length
        body = soup.find("body")
        text = body.get_text(separator=" ", strip=True) if body else ""
        word_count = len(text.split())
        if word_count < 300:
            issues.append("thin_content")

        # Images
        images = soup.find_all("img")
        images_no_alt = [img for img in images if not img.get("alt")]
        if images_no_alt:
            issues.append(f"images_without_alt:{len(images_no_alt)}")

        # Internal links
        parsed = urlparse(url)
        internal_links = 0
        for a in soup.find_all("a", href=True):
            full = urljoin(url, a["href"])
            if urlparse(full).netloc == parsed.netloc:
                internal_links += 1

        # Canonical
        canonical = soup.find("link", rel="canonical")
        if not canonical:
            issues.append("missing_canonical")

        return {
            "url": url,
            "title": title[:120],
            "meta_description": meta_desc[:200],
            "h1": h1_tags[0].get_text(strip=True) if h1_tags else "",
            "word_count": word_count,
            "internal_links": internal_links,
            "images_total": len(images),
            "images_no_alt": len(images_no_alt),
            "issues": issues,
        }

    except Exception as exc:
        return {"url": url, "issues": [f"error: {str(exc)[:100]}"], "word_count": 0}


def main():
    config = load_input()
    domain = config["domain"]
    max_pages = config.get("max_pages", 20)

    # Discover pages
    urls = fetch_sitemap_urls(domain, max_pages)
    print(f"Found {len(urls)} URLs to audit", file=sys.stderr)

    # Audit each page
    audits = []
    for url in urls:
        audit = audit_page(url)
        audits.append(audit)
        rate_limit(1.0, 2.0)

    # Summarize issues
    issue_counts = {}
    pages_with_issues = 0
    total_word_count = 0
    for audit in audits:
        if audit.get("issues"):
            pages_with_issues += 1
        for issue in audit.get("issues", []):
            base_issue = issue.split(":")[0]
            issue_counts[base_issue] = issue_counts.get(base_issue, 0) + 1
        total_word_count += audit.get("word_count", 0)

    avg_word_count = total_word_count // len(audits) if audits else 0

    # Build recommendations
    recommendations = []
    if issue_counts.get("missing_meta_description", 0) > 0:
        count = issue_counts["missing_meta_description"]
        recommendations.append({
            "title": f"Add meta descriptions to {count} pages",
            "rationale": "Missing meta descriptions reduce click-through rates from SERPs.",
            "impact_estimate": "medium",
            "effort": "low",
            "priority": 70,
        })
    if issue_counts.get("thin_content", 0) > 0:
        count = issue_counts["thin_content"]
        recommendations.append({
            "title": f"Expand thin content on {count} pages (under 300 words)",
            "rationale": "Thin content pages struggle to rank. Aim for 800+ words on key pages.",
            "impact_estimate": "high",
            "effort": "high",
            "priority": 60,
        })
    if issue_counts.get("images_without_alt", 0) > 0:
        count = issue_counts["images_without_alt"]
        recommendations.append({
            "title": f"Add alt text to images on {count} pages",
            "rationale": "Missing alt text hurts image search visibility and accessibility.",
            "impact_estimate": "low",
            "effort": "low",
            "priority": 45,
        })
    if issue_counts.get("missing_h1", 0) > 0:
        recommendations.append({
            "title": f"Add H1 headings to {issue_counts['missing_h1']} pages",
            "rationale": "H1 is a primary on-page ranking signal.",
            "impact_estimate": "medium",
            "effort": "low",
            "priority": 65,
        })

    finding = build_finding(
        source_role="content_audit",
        headline=f"Audited {len(audits)} pages on {domain}; {pages_with_issues} have SEO issues",
        metrics=[
            {"name": "Pages audited", "value": len(audits)},
            {"name": "Pages with issues", "value": pages_with_issues},
            {"name": "Avg word count", "value": avg_word_count},
            {"name": "Total issues found", "value": sum(issue_counts.values())},
        ],
        recommendations=recommendations,
        evidence=[
            f"Issue breakdown: {issue_counts}",
            f"Pages from sitemap: {len(urls)}",
            f"Avg content length: {avg_word_count} words",
        ],
        confidence=0.75,
        raw_notes="\n".join(
            f"- {a['url']}: {a.get('word_count', 0)} words, issues: {a.get('issues', [])}"
            for a in audits[:20]
        ),
    )

    output_finding(finding)


if __name__ == "__main__":
    main()
