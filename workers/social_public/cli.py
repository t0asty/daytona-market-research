from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from workers.social_public.finding import build_organic_social_finding
from workers.social_public.youtube_playwright import scrape_youtube_video_rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape a public YouTube channel video listing and emit AgentFinding JSON.",
    )
    parser.add_argument(
        "--channel-url",
        required=True,
        help="YouTube channel videos URL, e.g. https://www.youtube.com/@SomeBrand/videos",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=10,
        help="Maximum videos to sample from the listing (default: 10).",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="/tmp/social_snapshot.finding.json",
        help="Write finding JSON here (default: /tmp/social_snapshot.finding.json).",
    )
    parser.add_argument(
        "--mode",
        choices=("playwright", "agent"),
        default="playwright",
        help="playwright: deterministic DOM scrape; agent: browser-use + ChatOpenAI (optional extra).",
    )
    parser.add_argument(
        "--print",
        dest="print_json",
        action="store_true",
        help="Also print JSON to stdout.",
    )
    args = parser.parse_args()

    if args.mode == "playwright":
        scraped = scrape_youtube_video_rows(
            args.channel_url,
            max_items=args.max_items,
        )
        finding = build_organic_social_finding(
            channel_url=args.channel_url,
            videos=scraped.videos,
            agent_id="playwright-youtube",
            partial=scraped.partial or bool(scraped.error),
        )
        if scraped.error:
            raw = finding.raw_notes or ""
            finding = finding.model_copy(
                update={"raw_notes": (raw + "\nScrape error: " + scraped.error).strip()}
            )
    else:
        from workers.social_public.browser_use_runner import run_browser_use_youtube_sample

        finding = asyncio.run(
            run_browser_use_youtube_sample(args.channel_url, max_items=args.max_items)
        )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(finding.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {out_path}", file=sys.stderr)
    if args.print_json:
        print(json.dumps(finding.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
