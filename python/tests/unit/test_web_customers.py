from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from robocap_decryption_sdk.models.key_meta import RsaKeyMeta
from robocap_decryption_sdk.services.rsa_import import import_rsa_key_version
from tests.helpers import generate_rsa_keypair


def test_set_active_customer(web_client: TestClient, tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    pub, priv = generate_rsa_keypair(bits=2048)
    import_rsa_key_version(
        "cust_a",
        pub,
        priv,
        RsaKeyMeta(
            rsa_key_version=1,
            effective_at=datetime.now(timezone.utc),
            device_id="cust_a",
            rsa_bits=2048,
        ),
        sdk_root=vault,
    )

    resp = web_client.put(
        "/api/customers/active",
        json={"vault_path": str(vault), "customer_id": "cust_a"},
    )
    assert resp.status_code == 200

    listed = web_client.get("/api/customers", params={"vault_path": str(vault)})
    assert listed.json()["data"]["active_customer_id"] == "cust_a"
