from __future__ import annotations

from pathlib import Path

import pytest

from robocap_decryption_sdk.errors import ErrorCode, RobocapError
from robocap_decryption_sdk.services.rsa_delete import delete_rsa_key_dir, delete_rsa_key_version
from robocap_decryption_sdk.vault.key_vault import KeyVault
from robocap_decryption_sdk.vault.layout import ensure_private_dir
from tests.helpers import generate_rsa_keypair
from tests.helpers_cenc import import_cenc_rsa_v1, import_cenc_rsa_vN


def test_delete_rsa_version_removes_v2_keeps_v1(sdk_root: Path) -> None:
    customer_id = "CUST_DEL"
    pub_v1, priv_v1 = generate_rsa_keypair(bits=2048)
    pub_v2, priv_v2 = generate_rsa_keypair(bits=2048)
    import_cenc_rsa_vN(sdk_root, customer_id, pub_v1, priv_v1, 1)
    import_cenc_rsa_vN(sdk_root, customer_id, pub_v2, priv_v2, 2)

    vault = KeyVault(sdk_root)
    assert vault.rsa_version_dir(customer_id, 2).is_dir()

    result = delete_rsa_key_version(customer_id, 2, sdk_root=sdk_root)
    assert result.folder_name == "v2"

    assert not vault.rsa_version_dir(customer_id, 2).exists()
    assert vault.rsa_version_dir(customer_id, 1).is_dir()
    assert vault.list_rsa_versions(customer_id) == [1]


def test_list_rsa_key_dirs_includes_non_standard_name(sdk_root: Path) -> None:
    customer_id = "CUST_DEL"
    pub, priv = generate_rsa_keypair(bits=2048)
    import_cenc_rsa_v1(sdk_root, customer_id, pub, priv)

    vault = KeyVault(sdk_root)
    custom = vault.rsa_dir(customer_id) / "v5_test"
    ensure_private_dir(custom)
    (custom / "public.pem").write_bytes(vault.public_pem(customer_id, 1).read_bytes())
    (custom / "private.pem").write_bytes(vault.private_pem(customer_id, 1).read_bytes())

    dirs = vault.list_rsa_key_dirs(customer_id)
    assert [p.name for p in dirs] == ["v1", "v5_test"]


def test_delete_rsa_key_dir_non_standard_name(sdk_root: Path) -> None:
    customer_id = "CUST_DEL"
    pub, priv = generate_rsa_keypair(bits=2048)
    import_cenc_rsa_v1(sdk_root, customer_id, pub, priv)

    vault = KeyVault(sdk_root)
    custom = vault.rsa_dir(customer_id) / "v5_test"
    ensure_private_dir(custom)
    (custom / "public.pem").write_bytes(pub)
    (custom / "private.pem").write_bytes(priv)

    result = delete_rsa_key_dir(customer_id, custom, sdk_root=sdk_root)
    assert result.folder_name == "v5_test"
    assert not custom.exists()
    assert vault.rsa_version_dir(customer_id, 1).is_dir()


def test_delete_rsa_key_dir_rejects_outside_rsa_dir(sdk_root: Path) -> None:
    customer_id = "CUST_DEL"
    pub, priv = generate_rsa_keypair(bits=2048)
    import_cenc_rsa_v1(sdk_root, customer_id, pub, priv)

    outside = sdk_root / "outside"
    outside.mkdir()

    with pytest.raises(RobocapError) as exc_info:
        delete_rsa_key_dir(customer_id, outside, sdk_root=sdk_root)
    assert exc_info.value.code == ErrorCode.ERR_RSA_VERSION_MISSING


def test_delete_missing_version_raises(sdk_root: Path) -> None:
    customer_id = "CUST_DEL"
    pub, priv = generate_rsa_keypair(bits=2048)
    import_cenc_rsa_v1(sdk_root, customer_id, pub, priv)

    with pytest.raises(RobocapError) as exc_info:
        delete_rsa_key_version(customer_id, 99, sdk_root=sdk_root)
    assert exc_info.value.code == ErrorCode.ERR_RSA_VERSION_MISSING


def test_delete_missing_customer_raises(sdk_root: Path) -> None:
    with pytest.raises(RobocapError) as exc_info:
        delete_rsa_key_version("NO_SUCH_CUST", 1, sdk_root=sdk_root)
    assert exc_info.value.code == ErrorCode.ERR_CUSTOMER_NOT_FOUND
