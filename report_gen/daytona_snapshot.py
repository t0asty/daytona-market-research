"""SEO-specific Daytona snapshot creation.

Creates a snapshot pre-loaded with web scraping libraries for SEO research.
Uses env vars directly (no Jentic dependency).

Usage:
    DAYTONA_API_KEY=... python -m report_gen.daytona_snapshot
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


async def create_seo_snapshot(
    snapshot_name: str | None = None,
) -> None:
    """Create the SEO agent snapshot in Daytona Cloud.

    Pre-installs web scraping libraries so sandbox creation is fast.
    Resources are minimal (cpu=1, memory=2) since SEO scripts are I/O-bound.
    """
    from report_gen.daytona_imports import load_daytona

    d = load_daytona()
    CreateSnapshotParams = d.CreateSnapshotParams
    Daytona = d.Daytona
    DaytonaConfig = d.DaytonaConfig
    Image = d.Image
    Resources = d.Resources

    snapshot_name = snapshot_name or os.environ.get("SEO_SNAPSHOT_NAME", "seo-agent-v1")

    config = DaytonaConfig(
        api_key=os.environ["DAYTONA_API_KEY"],
        api_url=os.environ.get("DAYTONA_API_URL", "https://app.daytona.io/api"),
        target=os.environ.get("DAYTONA_TARGET", "us"),
    )
    daytona = Daytona(config)

    image = (
        Image.debian_slim("3.12")
        .run_commands(
            "apt-get update && apt-get install -y --no-install-recommends "
            "curl libxml2-dev libxslt1-dev",
        )
        .pip_install([
            "requests>=2.31",
            "beautifulsoup4>=4.12",
            "lxml>=5.1",
            "urllib3>=2.0",
        ])
        .workdir("/home/daytona")
    )

    logger.info("Creating SEO snapshot '%s'...", snapshot_name)
    daytona.snapshot.create(
        CreateSnapshotParams(
            name=snapshot_name,
            image=image,
            resources=Resources(cpu=1, memory=2, disk=5),
        ),
        on_logs=lambda chunk: logger.info("  %s", chunk.rstrip()),
    )
    logger.info("SEO snapshot '%s' created successfully.", snapshot_name)


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(create_seo_snapshot())
