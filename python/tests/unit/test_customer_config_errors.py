from __future__ import annotations

import json
from pathlib import Path

import pytest

from robocap_decryption_sdk.errors import ErrorCode, RobocapError

from robocap_customer.config import CustomerConfig
from robocap_customer.error_mapper import (
    MSG_CENC,
    MSG_CORRUPT,
    MSG_OWNERSHIP,
    MSG_OUTPUT_PERM,
    MSG_SKIP,
    MSG_VAULT_BAD,
    to_message,
)


def test_config_load_missing_returns_none(tmp_path: Path) -> None:
    assert CustomerConfig.load(tmp_path) is None


def test_config_load_valid(tmp_path: Path) -> None:
    path = tmp_path / "customer_config.json"
    path.write_text(
        json.dumps(
            {
                "customer_id": "CUST_001",
                "vault_root": str(tmp_path),
                "user_private_key_path": "D:/keys/user.pem",
            }
        ),
        encoding="utf-8",
    )
    cfg = CustomerConfig.load(tmp_path)
    assert cfg is not None
    assert cfg.customer_id == "CUST_001"
    assert cfg.user_private_key_path == Path("D:/keys/user.pem")


def test_config_load_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "customer_config.json").write_text("{bad", encoding="utf-8")
    assert CustomerConfig.load(tmp_path) is None


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (ErrorCode.ERR_CUSTOMER_NOT_FOUND, MSG_OWNERSHIP),
        (ErrorCode.ERR_KEY_OWNERSHIP_FAILED, MSG_OWNERSHIP),
        (ErrorCode.ERR_CUSTOMER_MISMATCH, MSG_OWNERSHIP),
        (ErrorCode.ERR_CENC_TAGS_MISSING, MSG_CORRUPT),
        (ErrorCode.ERR_VAULT_IO, MSG_OUTPUT_PERM),
        (ErrorCode.ERR_CENC_CUSTOMER_ID_INVALID, MSG_CORRUPT),
        (ErrorCode.ERR_CENC_CEKA_TRIAL_FAILED, MSG_CENC),
        (ErrorCode.ERR_RSA_VERSION_MISSING, MSG_SKIP),
    ],
)
def test_error_mapping(code: ErrorCode, expected: str) -> None:
    assert to_message(RobocapError(code, "internal detail")) == expected
    assert "ERR_" not in to_message(RobocapError(code, "internal detail"))
    assert "internal" not in to_message(RobocapError(code, "internal detail"))


def test_permission_error_maps_to_output_perm() -> None:
    assert to_message(PermissionError("denied")) == MSG_OUTPUT_PERM


def test_vault_bad_message_constant() -> None:
    assert MSG_VAULT_BAD == "Key vault not found or invalid."
