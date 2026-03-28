"""Technical SEO Agent — checks site health and technical signals.

Input (input.json):
    domain: str — target domain

Output: AgentFinding JSON to stdout
"""

import json
import sys
import time
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup
from common import (
    build_finding,
    get_headers,
    load_input,
    output_finding,
    rate_limit,
)


def check_robots_txt(domain: str) -> dict:
    """Check robots.txt existence and content."""
    url = f"https://{domain}/robots.txt"
    try:
        resp = requests.get(url, headers=get_headers(), timeout=10)
        if resp.status_code == 200:
            text = resp.text
            has_sitemap = "sitemap:" in text.lower()
            has_disallow = "disallow:" in text.lower()
            return {
                "name": "robots.txt",
                "status": "pass",
                "details": f"Found ({len(text)} bytes). Sitemap ref: {has_sitemap}. Has disallow rules: {has_disallow}",
            }
        return {"name": "robots.txt", "status": "fail", "details": f"HTTP {resp.status_code}", "recommendation": "Create a robots.txt file"}
    except Exception as exc:
        return {"name": "robots.txt", "status": "error", "details": str(exc)[:100]}


def check_sitemap(domain: str) -> dict:
    """Check sitemap.xml existence."""
    for path in ["/sitemap.xml", "/sitemap_index.xml"]:
        url = f"https://{domain}{path}"
        try:
            resp = requests.get(url, headers=get_headers(), timeout=10)
            if resp.status_code == 200:
                try:
                    root = ElementTree.fromstring(resp.content)
                    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                    urls = root.findall(".//sm:url", ns)
                    sitemaps = root.findall(".//sm:sitemap", ns)
                    count = len(urls) or len(sitemaps)
                    return {
                        "name": "sitemap.xml",
                        "status": "pass",
                        "details": f"Found at {path} with {count} entries",
                    }
                except Exception:
                    return {"name": "sitemap.xml", "status": "warn", "details": f"Found at {path} but XML parse failed"}
        except Exception:
            continue

    return {"name": "sitemap.xml", "status": "fail", "details": "Not found", "recommendation": "Create an XML sitemap and submit to Google Search Console"}


def check_https(domain: str) -> dict:
    """Check HTTPS and redirect from HTTP."""
    try:
        resp = requests.get(f"http://{domain}", timeout=10, allow_redirects=True)
        final_url = resp.url
        if final_url.startswith("https://"):
            return {"name": "HTTPS", "status": "pass", "details": f"HTTP redirects to {final_url}"}
        return {"name": "HTTPS", "status": "fail", "details": "No HTTPS redirect", "recommendation": "Enable HTTPS redirect"}
    except Exception as exc:
        return {"name": "HTTPS", "status": "error", "details": str(exc)[:100]}


def check_page_speed(domain: str) -> dict:
    """Measure basic page load time."""
    url = f"https://{domain}"
    try:
        start = time.time()
        resp = requests.get(url, headers=get_headers(), timeout=15)
        load_time = round(time.time() - start, 2)

        size_kb = len(resp.content) / 1024
        status = "pass" if load_time < 3.0 else "warn" if load_time < 5.0 else "fail"
        recommendation = f"Optimize page load time (currently {load_time}s)" if status != "pass" else None

        result = {
            "name": "Page speed",
            "status": status,
            "details": f"Load time: {load_time}s, Size: {round(size_kb)}KB",
        }
        if recommendation:
            result["recommendation"] = recommendation
        return result
    except Exception as exc:
        return {"name": "Page speed", "status": "error", "details": str(exc)[:100]}


def check_structured_data(domain: str) -> dict:
    """Check for JSON-LD structured data."""
    url = f"https://{domain}"
    try:
        resp = requests.get(url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        scripts = soup.find_all("script", type="application/ld+json")

        if not scripts:
            return {
                "name": "Structured data",
                "status": "fail",
                "details": "No JSON-LD found",
                "recommendation": "Add Organization and WebSite schema markup",
            }

        types = []
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    types.append(data.get("@type", "Unknown"))
                elif isinstance(data, list):
                    types.extend(d.get("@type", "Unknown") for d in data if isinstance(d, dict))
            except Exception:
                pass

        return {
            "name": "Structured data",
            "status": "pass",
            "details": f"JSON-LD types: {', '.join(types)}",
        }
    except Exception as exc:
        return {"name": "Structured data", "status": "error", "details": str(exc)[:100]}


def check_mobile_viewport(domain: str) -> dict:
    """Check for mobile viewport meta tag."""
    url = f"https://{domain}"
    try:
        resp = requests.get(url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        viewport = soup.find("meta", attrs={"name": "viewport"})

        if viewport:
            content = viewport.get("content", "")
            return {"name": "Mobile viewport", "status": "pass", "details": f"viewport: {content[:80]}"}
        return {
            "name": "Mobile viewport",
            "status": "fail",
            "details": "No viewport meta tag",
            "recommendation": "Add <meta name='viewport' content='width=device-width, initial-scale=1'>",
        }
    except Exception as exc:
        return {"name": "Mobile viewport", "status": "error", "details": str(exc)[:100]}


def check_canonical(domain: str) -> dict:
    """Check for canonical tag on homepage."""
    url = f"https://{domain}"
    try:
        resp = requests.get(url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        canonical = soup.find("link", rel="canonical")

        if canonical:
            href = canonical.get("href", "")
            return {"name": "Canonical tag", "status": "pass", "details": f"canonical: {href[:80]}"}
        return {
            "name": "Canonical tag",
            "status": "warn",
            "details": "No canonical tag on homepage",
            "recommendation": "Add self-referencing canonical tag to prevent duplicate content issues",
        }
    except Exception as exc:
        return {"name": "Canonical tag", "status": "error", "details": str(exc)[:100]}


def main():
    config = load_input()
    domain = config["domain"]

    checks = []
    check_funcs = [
        check_robots_txt,
        check_sitemap,
        check_https,
        check_page_speed,
        check_structured_data,
        check_mobile_viewport,
        check_canonical,
    ]

    for func in check_funcs:
        result = func(domain)
        checks.append(result)
        rate_limit(0.5, 1.0)

    # Score
    passed = sum(1 for c in checks if c["status"] == "pass")
    failed = sum(1 for c in checks if c["status"] == "fail")
    warnings = sum(1 for c in checks if c["status"] == "warn")
    score = round(passed / len(checks) * 100) if checks else 0

    # Build recommendations from failed checks
    recommendations = []
    for check in checks:
        if check.get("recommendation"):
            priority = 80 if check["status"] == "fail" else 50
            recommendations.append({
                "title": check["recommendation"],
                "rationale": f"{check['name']}: {check['details']}",
                "impact_estimate": "high" if check["status"] == "fail" else "medium",
                "effort": "low",
                "priority": priority,
            })

    finding = build_finding(
        source_role="technical_seo",
        headline=f"Technical SEO score: {score}% ({passed}/{len(checks)} checks passed) for {domain}",
        metrics=[
            {"name": "Technical SEO score", "value": score, "unit": "%"},
            {"name": "Checks passed", "value": passed},
            {"name": "Checks failed", "value": failed},
            {"name": "Warnings", "value": warnings},
        ],
        recommendations=recommendations,
        evidence=[
            f"{c['name']}: {c['status']} — {c['details']}" for c in checks
        ],
        confidence=0.8,
        raw_notes=json.dumps(checks, indent=2),
    )

    output_finding(finding)


if __name__ == "__main__":
    main()
