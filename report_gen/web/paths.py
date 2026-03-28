from __future__ import annotations

import os
from pathlib import Path


def resolve_fixtures_dir() -> Path:
    """Directory containing `*.json` agent findings (repo `examples/fixtures` in dev)."""
    env = os.environ.get("FINDINGS_FIXTURES_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve().parent
    for base in [here, *here.parents]:
        cand = base / "examples" / "fixtures"
        if cand.is_dir():
            return cand.resolve()
    return Path("examples/fixtures").resolve()


def resolve_frontend_dist_dir() -> Path | None:
    """
    Built Vite output (`frontend/dist`) for serving the SPA from this API.
    Uses UI_STATIC_DIR when set and valid; otherwise walks up from this package to find `frontend/dist`.
    """
    env = os.environ.get("UI_STATIC_DIR", "").strip()
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env).expanduser().resolve())
    here = Path(__file__).resolve().parent
    for base in [here, *here.parents]:
        candidates.append((base / "frontend" / "dist").resolve())
    candidates.append((Path.cwd() / "frontend" / "dist").resolve())

    seen: set[Path] = set()
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        if cand.is_dir() and (cand / "index.html").is_file():
            return cand
    return None
