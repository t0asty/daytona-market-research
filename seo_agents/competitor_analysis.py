"""Competitor Analysis Agent — analyzes competitor page structure and content.

Input (input.json):
    domain: str — target domain
    competitors: list[str] — competitor domains to analyze
    serp_data: dict — SERP findings from previous stage (optional)

Output: AgentFinding JSON to stdout
"""

import sys
from urllib.parse import urljoin, urlparse

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


def analyze_page(url: str) -> dict | None:
    """Analyze a single page for SEO-relevant signals."""
    try:
        resp = retry_request(
            lambda: requests.get(url, headers=get_headers(), timeout=15, allow_redirects=True)
        )
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # Title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Meta description
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "")

        # Headings
        headings = {}
        for level in range(1, 4):
            tags = soup.find_all(f"h{level}")
            headings[f"h{level}"] = [t.get_text(strip=True) for t in tags[:5]]

        # Content
        body = soup.find("body")
        text = body.get_text(separator=" ", strip=True) if body else ""
        word_count = len(text.split())

        # Links
        internal_links = 0
        external_links = 0
        parsed_url = urlparse(url)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("#") or href.startswith("javascript:"):
                continue
            full_url = urljoin(url, href)
            link_domain = urlparse(full_url).netloc
            if link_domain == parsed_url.netloc:
                internal_links += 1
            else:
                external_links += 1

        # Schema/structured data
        schemas = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and "@type" in data:
                    schemas.append(data["@type"])
                elif isinstance(data, list):
                    schemas.extend(d.get("@type", "") for d in data if isinstance(d, dict))
            except Exception:
                pass

        # Images without alt
        images_total = len(soup.find_all("img"))
        images_no_alt = len([img for img in soup.find_all("img") if not img.get("alt")])

        return {
            "url": url,
            "title": title[:120],
            "meta_description": meta_desc[:200],
            "word_count": word_count,
            "headings": headings,
            "internal_links": internal_links,
            "external_links": external_links,
            "schema_types": schemas,
            "images_total": images_total,
            "images_no_alt": images_no_alt,
        }

    except Exception as exc:
        print(f"Page analysis failed for {url}: {exc}", file=sys.stderr)
        return None


def discover_competitors_from_serp(serp_data: dict, target_domain: str) -> list[str]:
    """Extract competitor domains from SERP data."""
    competitors = set()
    target_netloc = target_domain.replace("www.", "")

    findings = serp_data.get("findings", {})
    serp_finding = findings.get("serp_analysis", {})

    # This is a simplified extraction — in practice the SERP data structure varies
    for key, val in serp_finding.items():
        if isinstance(val, str) and "." in val and "/" not in val:
            if target_netloc not in val:
                competitors.add(val)

    return list(competitors)[:5]


def main():
    config = load_input()
    domain = config["domain"]
    competitors = config.get("competitors", [])
    serp_data = config.get("serp_data", {})

    # Auto-discover competitors from SERP data if none provided
    if not competitors and serp_data:
        competitors = discover_competitors_from_serp(serp_data, domain)

    if not competitors:
        # Fallback: just analyze the target domain itself
        competitors = []

    # Analyze target domain homepage
    target_url = f"https://{domain}" if not domain.startswith("http") else domain
    target_analysis = analyze_page(target_url)
    rate_limit(1.0, 2.0)

    # Analyze competitor homepages
    competitor_analyses = []
    for comp in competitors[:5]:
        comp_url = f"https://{comp}" if not comp.startswith("http") else comp
        analysis = analyze_page(comp_url)
        if analysis:
            analysis["competitor_domain"] = comp
            competitor_analyses.append(analysis)
        rate_limit(1.0, 2.0)

    # Identify content gaps
    content_gaps = []
    if target_analysis and competitor_analyses:
        avg_comp_words = sum(c["word_count"] for c in competitor_analyses) / len(competitor_analyses)
        if target_analysis["word_count"] < avg_comp_words * 0.7:
            content_gaps.append(f"Homepage content ({target_analysis['word_count']} words) is {int((1 - target_analysis['word_count']/avg_comp_words) * 100)}% shorter than competitor average ({int(avg_comp_words)} words)")

        # Schema gap
        comp_schemas = set()
        for c in competitor_analyses:
            comp_schemas.update(c.get("schema_types", []))
        target_schemas = set(target_analysis.get("schema_types", []))
        missing_schemas = comp_schemas - target_schemas
        if missing_schemas:
            content_gaps.append(f"Missing schema types used by competitors: {', '.join(missing_schemas)}")

    recommendations = []
    if content_gaps:
        recommendations.append({
            "title": "Address content gaps vs competitors",
            "rationale": "; ".join(content_gaps[:3]),
            "impact_estimate": "high",
            "effort": "medium",
            "priority": 75,
        })

    if competitor_analyses:
        avg_internal = sum(c["internal_links"] for c in competitor_analyses) / len(competitor_analyses)
        if target_analysis and target_analysis["internal_links"] < avg_internal * 0.5:
            recommendations.append({
                "title": "Improve internal linking structure",
                "rationale": f"Target has {target_analysis['internal_links']} internal links vs competitor avg of {int(avg_internal)}",
                "impact_estimate": "medium",
                "effort": "low",
                "priority": 65,
            })

    finding = build_finding(
        source_role="competitor_analysis",
        headline=f"Analyzed {len(competitor_analyses)} competitors for {domain}; {len(content_gaps)} content gaps identified",
        metrics=[
            {"name": "Competitors analyzed", "value": len(competitor_analyses)},
            {"name": "Content gaps found", "value": len(content_gaps)},
            {"name": "Target word count", "value": target_analysis["word_count"] if target_analysis else 0},
            {"name": "Avg competitor word count", "value": int(sum(c["word_count"] for c in competitor_analyses) / len(competitor_analyses)) if competitor_analyses else 0},
        ],
        recommendations=recommendations,
        evidence=[
            f"Competitors: {', '.join(c.get('competitor_domain', 'unknown') for c in competitor_analyses)}",
            *content_gaps[:5],
        ],
        confidence=0.6 if competitor_analyses else 0.3,
        raw_notes="\n".join(
            f"- {c.get('competitor_domain', 'unknown')}: {c['word_count']} words, "
            f"{c['internal_links']} internal links, schemas: {c.get('schema_types', [])}"
            for c in competitor_analyses
        ) if competitor_analyses else "No competitors analyzed",
    )

    output_finding(finding)


if __name__ == "__main__":
    main()
