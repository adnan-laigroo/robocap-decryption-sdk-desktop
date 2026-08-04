from __future__ import annotations

import json
from pathlib import Path

import pytest

from robocap_decryption_sdk.errors import ErrorCode, RobocapError
from robocap_decryption_sdk.vault.key_vault import KeyVault

from robocap_customer.config import CustomerConfig
from robocap_customer.error_mapper import (
    MSG_BUNDLE_MISSING,
    MSG_IMPORT_CONFLICT,
    MSG_INVALID_CUSTOMER_ID,
    MSG_INVALID_KEY,
    to_import_message,
)
from robocap_customer.device_keys import (
    load_user_private_index,
    user_private_index_path,
    vault_user_private_path,
    vault_user_private_path_for_version,
)
from robocap_customer.import_prompts import ImportSessionInput, run_import
from robocap_customer.key_bundle import (
    PRIVATE_PEM_NAME,
    PUBLIC_PEM_NAME,
    USER_PRIVATE_PEM_NAME,
    default_user_private_path,
    load_key_bundle,
    validate_customer_id_input,
)
from robocap_customer.vault_bootstrap import (
    ensure_vault_layout,
    next_rsa_version,
)
from tests.helpers import generate_rsa_keypair
from tests.helpers_cenc import import_cenc_rsa_v1


def write_key_bundle(
    bundle_dir: Path,
    public_pem: bytes,
    private_pem: bytes,
    *,
    include_user_private: bool = True,
) -> None:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / PUBLIC_PEM_NAME).write_bytes(public_pem)
    (bundle_dir / PRIVATE_PEM_NAME).write_bytes(private_pem)
    if include_user_private:
        (bundle_dir / USER_PRIVATE_PEM_NAME).write_bytes(private_pem)


def test_ensure_vault_layout_creates_keys_dir(tmp_path: Path) -> None:
    vault_root = tmp_path / "my-company-keys"
    assert not vault_root.exists()
    ensure_vault_layout(vault_root)
    assert (vault_root / "vault" / "keys").is_dir()


def test_next_rsa_version_new_customer(tmp_path: Path) -> None:
    ensure_vault_layout(tmp_path)
    assert next_rsa_version(tmp_path, "frodobot_123") == 1


def test_next_rsa_version_after_v1(tmp_path: Path) -> None:
    ensure_vault_layout(tmp_path)
    pub, priv = generate_rsa_keypair(bits=2048)
    import_cenc_rsa_v1(tmp_path, "frodobot_123", pub, priv)
    assert next_rsa_version(tmp_path, "frodobot_123") == 2


def test_load_key_bundle_missing_files(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    with pytest.raises(Exception) as exc_info:
        load_key_bundle(bundle)
    assert exc_info.value.message == MSG_BUNDLE_MISSING


def test_load_key_bundle_mismatched_pair(tmp_path: Path) -> None:
    pub_a, priv_a = generate_rsa_keypair(bits=2048)
    _, priv_b = generate_rsa_keypair(bits=2048)
    bundle = tmp_path / "bundle"
    write_key_bundle(bundle, pub_a, priv_b, include_user_private=False)
    with pytest.raises(Exception) as exc_info:
        load_key_bundle(bundle)
    assert exc_info.value.message == MSG_INVALID_KEY


def test_load_key_bundle_wrong_bits(tmp_path: Path) -> None:
    pub, priv = generate_rsa_keypair(bits=4096)
    bundle = tmp_path / "bundle"
    write_key_bundle(bundle, pub, priv, include_user_private=False)
    with pytest.raises(Exception) as exc_info:
        load_key_bundle(bundle)
    assert exc_info.value.message == MSG_INVALID_KEY


def test_validate_customer_id_input() -> None:
    validate_customer_id_input("frodobot_123")
    with pytest.raises(Exception) as exc_info:
        validate_customer_id_input("bad id!")
    assert exc_info.value.message == MSG_INVALID_CUSTOMER_ID


def test_default_user_private_path(tmp_path: Path) -> None:
    pub, priv = generate_rsa_keypair(bits=2048)
    bundle = tmp_path / "bundle"
    write_key_bundle(bundle, pub, priv)
    assert default_user_private_path(bundle) == (bundle / USER_PRIVATE_PEM_NAME).resolve()
    assert default_user_private_path(tmp_path / "empty") is None


def test_run_import_v1_creates_vault_and_config(tmp_path: Path) -> None:
    vault_root = tmp_path / "my-company-keys"
    pub, priv = generate_rsa_keypair(bits=2048)
    bundle = tmp_path / "keys_v1"
    write_key_bundle(bundle, pub, priv)

    session = ImportSessionInput(
        vault_root=vault_root,
        customer_id="frodobot_123",
        key_bundle_dir=bundle,
        user_private_key_path=bundle / USER_PRIVATE_PEM_NAME,
    )
    result = run_import(session)

    assert result.rsa_key_version == 1
    vault = KeyVault(vault_root)
    assert vault.public_pem("frodobot_123", 1).is_file()
    cfg = CustomerConfig.load(vault_root)
    assert cfg is not None
    assert cfg.customer_id == "frodobot_123"
    assert cfg.vault_root == vault_root.resolve()
    assert cfg.user_private_key_path == (bundle / USER_PRIVATE_PEM_NAME).resolve()
    vault_pem = vault_user_private_path(vault_root, "frodobot_123")
    assert vault_pem.is_file()
    assert vault_pem.read_bytes() == priv
    version_pem = vault_user_private_path_for_version(vault_root, "frodobot_123", 1)
    assert version_pem.is_file()
    assert version_pem.read_bytes() == priv
    index = load_user_private_index(vault_root, "frodobot_123")
    assert index is not None
    assert index.active_version == 1
    assert user_private_index_path(vault_root, "frodobot_123").is_file()


def test_run_import_auto_increments_version(tmp_path: Path) -> None:
    vault_root = tmp_path / "vault"
    pub_v1, priv_v1 = generate_rsa_keypair(bits=2048)
    bundle_v1 = tmp_path / "keys_v1"
    write_key_bundle(bundle_v1, pub_v1, priv_v1)
    run_import(
        ImportSessionInput(
            vault_root=vault_root,
            customer_id="frodobot_123",
            key_bundle_dir=bundle_v1,
            user_private_key_path=bundle_v1 / USER_PRIVATE_PEM_NAME,
        )
    )

    pub_v2, priv_v2 = generate_rsa_keypair(bits=2048)
    bundle = tmp_path / "keys_v2"
    write_key_bundle(bundle, pub_v2, priv_v2)

    session = ImportSessionInput(
        vault_root=vault_root,
        customer_id="frodobot_123",
        key_bundle_dir=bundle,
        user_private_key_path=bundle / USER_PRIVATE_PEM_NAME,
    )
    result = run_import(session)
    assert result.rsa_key_version == 2
    assert KeyVault(vault_root).public_pem("frodobot_123", 2).is_file()
    v1_pem = vault_user_private_path_for_version(vault_root, "frodobot_123", 1)
    v2_pem = vault_user_private_path_for_version(vault_root, "frodobot_123", 2)
    assert v1_pem.is_file()
    assert v2_pem.is_file()
    assert v1_pem.read_bytes() == priv_v1
    assert v2_pem.read_bytes() == priv_v2
    assert v1_pem.read_bytes() != v2_pem.read_bytes()
    index = load_user_private_index(vault_root, "frodobot_123")
    assert index is not None
    assert index.active_version == 2


def test_import_error_mapping() -> None:
    assert (
        to_import_message(
            RobocapError(ErrorCode.ERR_CUSTOMER_ALREADY_EXISTS, "v2 exists")
        )
        == MSG_IMPORT_CONFLICT
    )
    assert (
        to_import_message(RobocapError(ErrorCode.ERR_INVALID_RSA_BITS, "4096"))
        == MSG_INVALID_KEY
    )
    assert "ERR_" not in to_import_message(
        RobocapError(ErrorCode.ERR_INVALID_RSA_BITS, "4096")
    )
