from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from robocap_sdk.models.key_meta import RsaKeyMeta
from robocap_sdk.services.rsa_import import import_rsa_key_version
from robocap_sdk.vault.key_vault import KeyVault
from tests.helpers import generate_rsa_keypair


@pytest.fixture
def sdk_root(tmp_path: Path) -> Path:
    return tmp_path / "sdk"


@pytest.fixture
def customer_setup(sdk_root: Path) -> dict:
    customer_id = "CUST_TEST"
    device_id = "DEV_TEST"
    public_pem, private_pem = generate_rsa_keypair(bits=2048)
    meta = RsaKeyMeta(
        rsa_key_version=1,
        effective_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        device_id=device_id,
        rsa_bits=2048,
    )
    import_rsa_key_version(
        customer_id,
        public_pem,
        private_pem,
        meta,
        sdk_root=sdk_root,
    )
    vault = KeyVault(sdk_root)
    return {
        "customer_id": customer_id,
        "device_id": device_id,
        "sdk_root": sdk_root,
        "public_pem": public_pem,
        "private_pem": private_pem,
        "vault": vault,
    }


@pytest.fixture
def web_client(tmp_path: Path):
    import os

    from fastapi.testclient import TestClient

    from robocap_web.config import Settings
    from robocap_web.main import create_app

    os.environ["DEV_MODE"] = "true"
    os.environ["ROBOCAP_WEB_MODE"] = "local"
    os.environ["ROBOCAP_DATA_ROOT"] = str(tmp_path / "data")
    settings = Settings()
    app = create_app(settings)
    with TestClient(app) as client:
        yield client
