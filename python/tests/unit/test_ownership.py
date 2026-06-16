from __future__ import annotations

from datetime import datetime, timezone

import pytest

from robocap_decryption_sdk.auth.ownership import verify_customer_private_key
from robocap_decryption_sdk.errors import ErrorCode, RobocapError
from robocap_decryption_sdk.models.key_meta import RsaKeyMeta
from robocap_decryption_sdk.services.rsa_import import import_rsa_key_version
from tests.helpers import generate_rsa_keypair


def test_ownership_match(sdk_root, customer_setup):
    result = verify_customer_private_key(
        customer_setup["customer_id"],
        customer_setup["private_pem"],
        sdk_root=sdk_root,
    )
    assert result.matched_rsa_key_version == 1


def test_ownership_wrong_key(sdk_root, customer_setup):
    _, other_private = generate_rsa_keypair()
    with pytest.raises(RobocapError) as exc:
        verify_customer_private_key(
            customer_setup["customer_id"],
            other_private,
            sdk_root=sdk_root,
        )
    assert exc.value.code == ErrorCode.ERR_KEY_OWNERSHIP_FAILED


def test_ownership_multi_version(sdk_root):
    customer_id = "CUST_MULTI"
    pub1, priv1 = generate_rsa_keypair(bits=2048)
    import_rsa_key_version(
        customer_id,
        pub1,
        priv1,
        RsaKeyMeta(
            rsa_key_version=1,
            effective_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            device_id="D1",
            rsa_bits=2048,
        ),
        sdk_root=sdk_root,
    )
    pub2, priv2 = generate_rsa_keypair(bits=2048)
    import_rsa_key_version(
        customer_id,
        pub2,
        priv2,
        RsaKeyMeta(
            rsa_key_version=2,
            effective_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            device_id="D1",
            rsa_bits=2048,
        ),
        sdk_root=sdk_root,
    )
    result = verify_customer_private_key(customer_id, priv2, sdk_root=sdk_root)
    assert result.matched_rsa_key_version == 2
