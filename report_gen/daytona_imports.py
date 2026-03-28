"""Load the Daytona Python SDK from either ``daytona`` (legacy) or ``daytona_sdk`` (current)."""

from __future__ import annotations

from typing import Any


def load_daytona() -> Any:
    """Return the top-level Daytona SDK module."""
    try:
        import daytona as pkg
    except ImportError:
        import daytona_sdk as pkg
    return pkg


def sdk_installed() -> bool:
    try:
        load_daytona()
    except ImportError:
        return False
    return True
