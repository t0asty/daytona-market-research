"""SERP Analysis Agent — analyzes search engine results pages.

Input (input.json):
    domain: str — target domain
    keywords: list[str] — keywords to analyze SERPs for

Output: AgentFinding JSON to stdout
"""

import sys
from collections import defaultdict
from urllib.parse import quote_plus, urlparse

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


def fetch_serp(keyword: str) -> dict:
    """Fetch and parse a Google SERP page for a keyword."""
    url = f"https://www.google.com/search?q={quote_plus(keyword)}&num=10&hl=en"
    result = {
        "keyword": keyword,
        "results": [],
        "features": [],
        "paa_questions": [],
    }

    try:
        resp = retry_request(
            lambda: requests.get(url, headers=get_headers(), timeout=15)
        )
        if resp.status_code != 200:
            print(f"SERP fetch returned {resp.status_code} for '{keyword}'", file=sys.stderr)
            return result

        soup = BeautifulSoup(resp.text, "lxml")

        # Extract organic results
        position = 0
        for g in soup.select("div.g, div[data-sokoban-container]"):
            link = g.select_one("a[href]")
            title_el = g.select_one("h3")
            snippet_el = g.select_one("div[data-sncf], span.st, div.VwiC3b")

            if link and title_el:
                position += 1
                href = link.get("href", "")
                result["results"].append({
                    "position": position,
                    "url": href,
                    "title": title_el.get_text(strip=True),
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    "domain": urlparse(href).netloc if href.startswith("http") else "",
                })

            if position >= 10:
                break

        # Detect SERP features
        if soup.select_one("div.xpdopen, div[data-attrid='wa:/description']"):
            result["features"].append("featured_snippet")
        if soup.select_one("div[data-initq]"):
            result["features"].append("people_also_ask")
        if soup.select_one("g-scrolling-carousel, div[data-lpage]"):
            result["features"].append("carousel")
        if soup.select_one("div.kno-rdesc, div[data-attrid]"):
            result["features"].append("knowledge_panel")
        if soup.select_one("div[id='rso'] video-voyager, div.P94G3e"):
            result["features"].append("video")

        # Extract People Also Ask questions
        for paa in soup.select("div[data-q]"):
            question = paa.get("data-q", "")
            if question:
                result["paa_questions"].append(question)

    except Exception as exc:
        print(f"SERP parse failed for '{keyword}': {exc}", file=sys.stderr)

    return result


def main():
    config = load_input()
    domain = config["domain"]
    keywords = config.get("keywords", [])[:20]  # Limit to avoid rate limiting

    if not keywords:
        output_finding(build_finding(
            source_role="serp_analysis",
            headline=f"No keywords provided for SERP analysis of {domain}",
            confidence=0.3,
        ))
        return

    serp_results = []
    feature_counts = defaultdict(int)
    total_paa = 0
    domain_positions = []

    for keyword in keywords:
        serp = fetch_serp(keyword)
        serp_results.append(serp)

        for feature in serp.get("features", []):
            feature_counts[feature] += 1
        total_paa += len(serp.get("paa_questions", []))

        # Check if target domain appears in results
        target_netloc = domain.replace("www.", "")
        for result in serp.get("results", []):
            if target_netloc in result.get("domain", ""):
                domain_positions.append(result["position"])

        rate_limit(2.0, 4.0)  # Longer delays for Google SERPs

    # Identify featured snippet opportunities
    snippet_opps = [
        s["keyword"] for s in serp_results
        if "featured_snippet" not in s.get("features", []) and s.get("results")
    ]

    # Find easy wins (keywords where we rank 4-10)
    easy_wins = []
    for serp in serp_results:
        target_netloc = domain.replace("www.", "")
        for r in serp.get("results", []):
            if target_netloc in r.get("domain", "") and 4 <= r["position"] <= 10:
                easy_wins.append({"keyword": serp["keyword"], "position": r["position"]})

    recommendations = []
    if snippet_opps:
        recommendations.append({
            "title": f"Target featured snippets for {len(snippet_opps)} keywords",
            "rationale": f"Keywords without featured snippets: {', '.join(snippet_opps[:5])}. "
                        "Creating structured content (lists, tables, definitions) can capture position 0.",
            "impact_estimate": "high",
            "effort": "medium",
            "priority": 80,
        })
    if easy_wins:
        recommendations.append({
            "title": f"Push {len(easy_wins)} keywords from page 1 bottom to top 3",
            "rationale": f"Currently ranking 4-10 for: {', '.join(w['keyword'] for w in easy_wins[:5])}. "
                        "Small content improvements can yield significant traffic gains.",
            "impact_estimate": "high",
            "effort": "low",
            "priority": 85,
        })

    avg_position = sum(domain_positions) / len(domain_positions) if domain_positions else 0

    finding = build_finding(
        source_role="serp_analysis",
        headline=f"Analyzed {len(serp_results)} SERPs; {len(easy_wins)} easy-win positions for {domain}",
        metrics=[
            {"name": "SERPs analyzed", "value": len(serp_results)},
            {"name": "Featured snippet opportunities", "value": len(snippet_opps)},
            {"name": "PAA questions found", "value": total_paa},
            {"name": "Domain appearances in top 10", "value": len(domain_positions)},
            {"name": "Avg domain position", "value": round(avg_position, 1) if avg_position else "Not ranked"},
            {"name": "Easy wins (position 4-10)", "value": len(easy_wins)},
        ],
        recommendations=recommendations,
        evidence=[
            f"SERP features distribution: {dict(feature_counts)}",
            f"Domain found in {len(domain_positions)}/{len(serp_results)} SERPs",
            f"Top PAA questions: {', '.join(q for s in serp_results for q in s.get('paa_questions', [])[:2])[:200]}",
        ],
        confidence=0.65,
        raw_notes="\n".join(
            f"- [{s['keyword']}] {len(s['results'])} results, features: {s['features']}"
            for s in serp_results[:20]
        ),
    )

    output_finding(finding)


if __name__ == "__main__":
    main()
