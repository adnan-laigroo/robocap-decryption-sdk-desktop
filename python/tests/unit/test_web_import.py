from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from robocap_customer.key_bundle import PRIVATE_PEM_NAME, PUBLIC_PEM_NAME
from tests.helpers import generate_rsa_keypair


def test_web_import_run(web_client: TestClient, tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    pub, priv = generate_rsa_keypair(bits=2048)
    (bundle / PUBLIC_PEM_NAME).write_bytes(pub)
    (bundle / PRIVATE_PEM_NAME).write_bytes(priv)
    user_pem = tmp_path / "user.pem"
    user_pem.write_bytes(priv)

    resp = web_client.post(
        "/api/import/run",
        json={
            "vault_path": str(vault),
            "customer_id": "web_cust",
            "bundle_path": str(bundle),
            "user_private_key_path": str(user_pem),
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["customer_id"] == "web_cust"
    assert data["rsa_key_version"] == 1


def test_web_generate_keys_subfolder(web_client, tmp_path: Path) -> None:
    parent = tmp_path / "key_root"
    parent.mkdir()
    resp = web_client.post(
        "/api/import/generate-keys",
        json={"bundle_path": str(parent), "layout": "subfolder"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["folder_name"] == "v1"
    assert Path(data["path"]).name == "v1"
    assert (Path(data["path"]) / PUBLIC_PEM_NAME).is_file()
    assert (Path(data["path"]) / PRIVATE_PEM_NAME).is_file()

    resp2 = web_client.post(
        "/api/import/generate-keys",
        json={"bundle_path": str(parent), "layout": "subfolder"},
    )
    assert resp2.json()["data"]["folder_name"] == "v2"
