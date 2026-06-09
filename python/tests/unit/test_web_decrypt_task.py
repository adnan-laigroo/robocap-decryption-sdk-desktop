from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from robocap_customer.batch_decryptor import BatchResult


@pytest.fixture
def decrypt_dirs(tmp_path: Path) -> dict[str, Path]:
    vault = tmp_path / "vault"
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    user_pem = tmp_path / "user.pem"
    input_root.mkdir()
    output_root.mkdir()
    user_pem.write_bytes(b"fake-pem")
    fake_mp4 = input_root / "clip.mp4"
    fake_mp4.write_bytes(b"not-a-real-mp4")
    return {
        "vault": vault,
        "input_root": input_root,
        "output_root": output_root,
        "user_pem": user_pem,
        "fake_mp4": fake_mp4,
    }


def test_decrypt_task_completes(
    web_client: TestClient,
    decrypt_dirs: dict[str, Path],
) -> None:
    mp4 = decrypt_dirs["fake_mp4"]

    def fake_run(session, resolver, *, progress_fn=None, cancel_check=None):
        if progress_fn:
            progress_fn(1, 1, mp4.name)
        return BatchResult(total=1, succeeded=1, failed=0, skipped=0)

    with patch(
        "robocap_web.services.decrypt_service.scan_cenc_mp4",
        return_value=[mp4],
    ), patch(
        "robocap_web.services.decrypt_service.run_decrypt_session",
        side_effect=fake_run,
    ):
        resp = web_client.post(
            "/api/decrypt/run",
            json={
                "vault_path": str(decrypt_dirs["vault"]),
                "user_private_key_path": str(decrypt_dirs["user_pem"]),
                "input_root": str(decrypt_dirs["input_root"]),
                "output_root": str(decrypt_dirs["output_root"]),
            },
        )
        assert resp.status_code == 200, resp.text
        task_id = resp.json()["data"]["task_id"]

        deadline = time.time() + 10
        status = "pending"
        while time.time() < deadline:
            snap = web_client.get(f"/api/decrypt/tasks/{task_id}")
            assert snap.status_code == 200
            status = snap.json()["data"]["status"]
            if status in ("completed", "failed"):
                break
            time.sleep(0.2)

    assert status == "completed"
    final = web_client.get(f"/api/decrypt/tasks/{task_id}").json()["data"]
    assert final["succeeded"] == 1
    assert final["failed"] == 0


def test_decrypt_scan_empty_dir(web_client: TestClient, tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with patch("robocap_web.services.decrypt_service.scan_cenc_mp4", return_value=[]):
        resp = web_client.post("/api/decrypt/scan", json={"input_root": str(empty)})
    assert resp.status_code == 200
    assert resp.json()["data"]["files"] == []
