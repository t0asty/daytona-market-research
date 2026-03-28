"""Run: python -m report_gen.web or serve-report-ui"""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("RELOAD", "1") == "1"
    uvicorn.run(
        "report_gen.web.server:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
