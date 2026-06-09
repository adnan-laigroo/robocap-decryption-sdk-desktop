from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(web_client: TestClient) -> None:
    resp = web_client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "ok"
    assert body["data"]["dev_mode"] is True
