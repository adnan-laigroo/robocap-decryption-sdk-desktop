from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from robocap_customer.key_bundle import PUBLIC_PEM_NAME, PRIVATE_PEM_NAME
from tests.helpers import generate_rsa_keypair
from robocap_sdk.models.key_meta import RsaKeyMeta
from robocap_sdk.services.rsa_import import import_rsa_key_version
from datetime import datetime, timezone


def test_delete_folders_always_list(web_client: TestClient, tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    pub, priv = generate_rsa_keypair(bits=2048)
    import_rsa_key_version(
        "del_cust",
        pub,
        priv,
        RsaKeyMeta(
            rsa_key_version=1,
            effective_at=datetime.now(timezone.utc),
            device_id="del_cust",
            rsa_bits=2048,
        ),
        sdk_root=vault,
    )

    resp = web_client.get(
        "/api/delete/folders",
        params={"vault_path": str(vault), "customer_id": "del_cust"},
    )
    assert resp.status_code == 200
    folders = resp.json()["data"]["folders"]
    assert len(folders) == 1
    assert folders[0]["index"] == 1
