"""Keyword Research Agent — discovers keywords via Google Suggest scraping.

Input (input.json):
    domain: str — target domain
    seed_keywords: list[str] — starting keywords
    locale: str — e.g. "en-US"
    max_keywords: int — limit

Output: AgentFinding JSON to stdout
"""

import sys
from collections import defaultdict
from urllib.parse import quote_plus

import requests
from common import (
    build_finding,
    get_headers,
    load_input,
    output_finding,
    rate_limit,
    retry_request,
)


def get_google_suggestions(query: str, locale: str = "en") -> list[str]:
    """Fetch Google autocomplete suggestions for a query."""
    lang = locale.split("-")[0] if "-" in locale else locale
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={quote_plus(query)}&hl={lang}"
    try:
        resp = retry_request(lambda: requests.get(url, headers=get_headers(), timeout=10))
        data = resp.json()
        return data[1] if len(data) > 1 else []
    except Exception as exc:
        print(f"Suggestion fetch failed for '{query}': {exc}", file=sys.stderr)
        return []


def classify_intent(keyword: str) -> str:
    """Simple intent classification based on keyword patterns."""
    kw = keyword.lower()
    if any(w in kw for w in ["buy", "price", "cost", "cheap", "deal", "discount", "order", "purchase"]):
        return "transactional"
    if any(w in kw for w in ["best", "top", "review", "compare", "vs", "alternative"]):
        return "commercial"
    if any(w in kw for w in ["how", "what", "why", "when", "guide", "tutorial", "tips"]):
        return "informational"
    return "navigational"


def cluster_keywords(keywords: list[dict]) -> dict[str, list[dict]]:
    """Group keywords by common root terms."""
    clusters: dict[str, list[dict]] = defaultdict(list)
    for kw in keywords:
        words = kw["keyword"].lower().split()
        # Use first 2 words as cluster key
        cluster_key = " ".join(words[:2]) if len(words) >= 2 else words[0] if words else "other"
        clusters[cluster_key].append(kw)
    return dict(clusters)


def main():
    config = load_input()
    domain = config["domain"]
    seeds = config.get("seed_keywords", [])
    locale = config.get("locale", "en-US")
    max_keywords = config.get("max_keywords", 50)

    if not seeds:
        # Generate seeds from domain name
        domain_name = domain.replace("www.", "").split(".")[0]
        seeds = [domain_name, f"{domain_name} services", f"{domain_name} reviews"]

    all_keywords = []
    seen = set()

    # Expand each seed keyword via Google Suggest
    for seed in seeds:
        suggestions = get_google_suggestions(seed, locale)
        for suggestion in suggestions:
            if suggestion.lower() not in seen and len(all_keywords) < max_keywords:
                seen.add(suggestion.lower())
                intent = classify_intent(suggestion)
                all_keywords.append({
                    "keyword": suggestion,
                    "intent": intent,
                    "source": f"suggest:{seed}",
                })
        rate_limit(0.5, 1.5)

        # Also try question variations
        for prefix in ["how to", "what is", "why"]:
            q = f"{prefix} {seed}"
            suggestions = get_google_suggestions(q, locale)
            for suggestion in suggestions:
                if suggestion.lower() not in seen and len(all_keywords) < max_keywords:
                    seen.add(suggestion.lower())
                    all_keywords.append({
                        "keyword": suggestion,
                        "intent": "informational",
                        "source": f"question:{prefix}+{seed}",
                    })
            rate_limit(0.5, 1.5)

        if len(all_keywords) >= max_keywords:
            break

    # Cluster keywords
    clusters = cluster_keywords(all_keywords)

    # Count intents
    intent_counts = defaultdict(int)
    for kw in all_keywords:
        intent_counts[kw["intent"]] += 1

    # Build recommendations from top clusters
    recommendations = []
    for cluster_name, cluster_kws in sorted(clusters.items(), key=lambda x: -len(x[1]))[:5]:
        recommendations.append({
            "title": f"Target '{cluster_name}' keyword cluster ({len(cluster_kws)} keywords)",
            "rationale": f"High-volume cluster with {len(cluster_kws)} related terms. "
                        f"Primary intent: {cluster_kws[0]['intent']}. "
                        f"Sample: {', '.join(k['keyword'] for k in cluster_kws[:3])}",
            "impact_estimate": "high" if len(cluster_kws) >= 5 else "medium",
            "effort": "medium",
            "priority": min(90, len(cluster_kws) * 10),
        })

    finding = build_finding(
        source_role="keyword_research",
        headline=f"Discovered {len(all_keywords)} keywords in {len(clusters)} clusters for {domain}",
        metrics=[
            {"name": "Keywords discovered", "value": len(all_keywords)},
            {"name": "Keyword clusters", "value": len(clusters)},
            {"name": "Informational intent", "value": intent_counts.get("informational", 0), "unit": "keywords"},
            {"name": "Transactional intent", "value": intent_counts.get("transactional", 0), "unit": "keywords"},
            {"name": "Commercial intent", "value": intent_counts.get("commercial", 0), "unit": "keywords"},
        ],
        recommendations=recommendations,
        evidence=[
            f"Google Suggest API: {len(seeds)} seed keywords expanded",
            f"Intent distribution: {dict(intent_counts)}",
            f"Top cluster: '{max(clusters, key=lambda k: len(clusters[k]))}' ({max(len(v) for v in clusters.values())} keywords)",
        ],
        confidence=0.7,
        raw_notes="\n".join(f"- {kw['keyword']} [{kw['intent']}]" for kw in all_keywords[:30]),
        extra={"_keywords": [kw["keyword"] for kw in all_keywords]},
    )

    output_finding(finding)


if __name__ == "__main__":
    main()
