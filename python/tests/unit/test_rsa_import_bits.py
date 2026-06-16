from __future__ import annotations

from datetime import datetime, timezone

import pytest

from robocap_decryption_sdk.errors import ErrorCode, RobocapError
from robocap_decryption_sdk.models.key_meta import RsaKeyMeta
from robocap_decryption_sdk.services.rsa_import import import_rsa_key_version
from tests.helpers import generate_rsa_keypair


def test_import_rsa_2048(sdk_root):
    customer_id = "CUST_2048"
    public_pem, private_pem = generate_rsa_keypair(bits=2048)
    result = import_rsa_key_version(
        customer_id,
        public_pem,
        private_pem,
        RsaKeyMeta(
            rsa_key_version=1,
            effective_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            device_id="DEV_2048",
            rsa_bits=2048,
        ),
        sdk_root=sdk_root,
    )
    assert result.rsa_key_version == 1


def test_import_rsa_invalid_bits(sdk_root):
    customer_id = "CUST_BAD"
    public_pem, private_pem = generate_rsa_keypair(bits=2048)
    with pytest.raises(RobocapError) as exc:
        import_rsa_key_version(
            customer_id,
            public_pem,
            private_pem,
            RsaKeyMeta(
                rsa_key_version=1,
                effective_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                device_id="DEV_BAD",
                rsa_bits=1024,
            ),
            sdk_root=sdk_root,
        )
    assert exc.value.code == ErrorCode.ERR_INVALID_RSA_BITS


def test_import_rsa_4096_rejected(sdk_root):
    customer_id = "CUST_4096"
    public_pem, private_pem = generate_rsa_keypair(bits=4096)
    with pytest.raises(RobocapError) as exc:
        import_rsa_key_version(
            customer_id,
            public_pem,
            private_pem,
            RsaKeyMeta(
                rsa_key_version=1,
                effective_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                device_id="DEV_4096",
                rsa_bits=4096,
            ),
            sdk_root=sdk_root,
        )
    assert exc.value.code == ErrorCode.ERR_INVALID_RSA_BITS
