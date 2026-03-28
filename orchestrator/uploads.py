from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def minimal_python_relative_paths() -> list[str]:
    """Paths required on PYTHONPATH inside a sandbox to run ``python -m orchestrator run …``."""
    root = repo_root()
    paths: list[str] = []
    fixed = [
        "report_gen/__init__.py",
        "report_gen/models.py",
        "workers/__init__.py",
        "workers/social_public/__init__.py",
        "workers/social_public/finding.py",
        "workers/social_public/mock_youtube.py",
        "workers/mock_agents/__init__.py",
        "workers/mock_agents/saas_b2b.py",
    ]
    for rel in fixed:
        paths.append(rel)

    orch = root / "orchestrator"
    for p in sorted(orch.rglob("*.py")):
        rel = p.relative_to(root).as_posix()
        if rel not in paths:
            paths.append(rel)
    return paths


def validate_minimal_tree() -> None:
    """Fail fast if the bundle is incomplete (e.g. after a refactor)."""
    root = repo_root()
    for rel in minimal_python_relative_paths():
        path = root / rel
        if not path.is_file():
            raise FileNotFoundError(f"Orchestrator bundle missing file: {rel}")
