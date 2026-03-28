from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from report_gen.web.server import app


def test_health() -> None:
    c = TestClient(app)
    r = c.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_fixtures_list() -> None:
    c = TestClient(app)
    r = c.get("/api/fixtures")
    assert r.status_code == 200
    data = r.json()
    assert "fixtures" in data
    assert len(data["fixtures"]) >= 1


def test_root_is_not_404() -> None:
    """GET / serves built SPA when frontend/dist exists, else a small HTML help page."""
    c = TestClient(app)
    r = c.get("/")
    assert r.status_code == 200
    body = r.text
    assert "Marketing report API" in body or 'id="root"' in body
