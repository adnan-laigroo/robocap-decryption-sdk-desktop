from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from robocap_decryption_sdk.errors import ErrorCode, RobocapError
from robocap_decryption_sdk.vault.key_vault import KeyVault

from robocap_customer.delete_prompts import (
    DeleteSessionInput,
    _key_dir_label,
    _pick_key_dir,
    run_delete,
)
from robocap_customer.error_mapper import (
    MSG_CUSTOMER_NOT_FOUND,
    MSG_DELETE_FAILED,
    MSG_VERSION_NOT_FOUND,
    to_delete_message,
)
from robocap_customer.vault_bootstrap import ensure_vault_layout
from tests.helpers import generate_rsa_keypair
from tests.helpers_cenc import import_cenc_rsa_v1, import_cenc_rsa_vN


def test_run_delete_removes_version(sdk_root: Path) -> None:
    ensure_vault_layout(sdk_root)
    customer_id = "frodobot_123"
    pub_v1, priv_v1 = generate_rsa_keypair(bits=2048)
    pub_v2, priv_v2 = generate_rsa_keypair(bits=2048)
    import_cenc_rsa_vN(sdk_root, customer_id, pub_v1, priv_v1, 1)
    import_cenc_rsa_vN(sdk_root, customer_id, pub_v2, priv_v2, 2)

    vault = KeyVault(sdk_root)
    key_dir = vault.rsa_version_dir(customer_id, 2)
    session = DeleteSessionInput(
        vault_root=sdk_root,
        customer_id=customer_id,
        key_dir=key_dir,
    )
    result = run_delete(session)
    assert result.folder_name == "v2"

    assert vault.list_rsa_versions(customer_id) == [1]
    assert not vault.rsa_version_dir(customer_id, 2).exists()


def test_pick_key_dir_second_choice(tmp_path: Path) -> None:
    a = tmp_path / "v1"
    b = tmp_path / "v2"
    a.mkdir()
    b.mkdir()
    with patch("robocap_customer.delete_prompts.input", return_value="2"):
        picked = _pick_key_dir("frodobot_123", [a.resolve(), b.resolve()])
    assert picked == b.resolve()


def test_key_dir_label() -> None:
    key_dir = Path("/vault/keys/frodobot_123/rsa/v5_test")
    assert _key_dir_label("frodobot_123", key_dir) == "frodobot_123/rsa/v5_test"


def test_delete_error_mapping() -> None:
    assert (
        to_delete_message(RobocapError(ErrorCode.ERR_CUSTOMER_NOT_FOUND, "x"))
        == MSG_CUSTOMER_NOT_FOUND
    )
    assert (
        to_delete_message(RobocapError(ErrorCode.ERR_RSA_VERSION_MISSING, "x"))
        == MSG_VERSION_NOT_FOUND
    )
    assert (
        to_delete_message(RobocapError(ErrorCode.ERR_VAULT_IO, "x"))
        != MSG_DELETE_FAILED
    )
