from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


@dataclass
class ScrapeResult:
    videos: list[dict[str, Any]]
    partial: bool
    error: str | None = None


def scrape_youtube_video_rows(
    channel_videos_url: str,
    *,
    max_items: int = 10,
    navigation_timeout_ms: int = 60_000,
    render_wait_ms: int = 2_500,
) -> ScrapeResult:
    """
    Load a YouTube channel **videos** tab (or similar listing) and extract visible rows.

    Selectors target common ``ytd-rich-item-renderer`` / ``ytd-video-renderer`` layouts; they may
    break when YouTube changes markup.
    """
    videos: list[dict[str, Any]] = []
    partial = False
    err: str | None = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                locale="en-US",
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.goto(channel_videos_url, wait_until="domcontentloaded", timeout=navigation_timeout_ms)

            # Consent / interstitial: best-effort dismiss (EU)
            for name in ("Accept all", "Reject all", "I agree", "Alles accepteren"):
                btn = page.get_by_role("button", name=name)
                if btn.count() > 0:
                    try:
                        btn.first.click(timeout=3_000)
                        page.wait_for_timeout(500)
                    except Exception:
                        partial = True

            try:
                page.wait_for_selector(
                    "ytd-rich-item-renderer, ytd-video-renderer",
                    timeout=navigation_timeout_ms,
                )
            except PlaywrightTimeoutError:
                partial = True
                err = err or "Timeout waiting for video grid selectors."

            page.wait_for_timeout(render_wait_ms)

            item_locator = page.locator("ytd-rich-item-renderer")
            if item_locator.count() == 0:
                item_locator = page.locator("ytd-video-renderer")

            count = min(item_locator.count(), max_items)
            for i in range(count):
                item = item_locator.nth(i)
                title_el = item.locator("a#video-title").first
                href = ""
                title = ""
                try:
                    href = title_el.get_attribute("href") or ""
                    title = title_el.inner_text(timeout=5_000).strip()
                except Exception:
                    partial = True
                if href.startswith("/"):
                    href = f"https://www.youtube.com{href}"

                views_text = ""
                meta = item.locator("span.inline-metadata-item, #metadata-line span")
                try:
                    nmeta = meta.count()
                    for j in range(nmeta):
                        t = meta.nth(j).inner_text(timeout=2_000).strip()
                        low = t.lower()
                        if "view" in low or any(ch.isdigit() for ch in t):
                            views_text = t
                            break
                except Exception:
                    partial = True

                videos.append({"title": title, "url": href, "views_text": views_text})

        except Exception as exc:
            partial = True
            err = str(exc)
        finally:
            browser.close()

    return ScrapeResult(videos=videos, partial=partial, error=err)
