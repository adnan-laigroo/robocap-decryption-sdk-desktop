from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import pytest

from robocap_customer.error_mapper import MSG_PREFLIGHT_KEY, CustomerFacingError
from robocap_customer.preflight import preflight_cenc_mp4
from robocap_customer.scanner import scan_cenc_mp4
from robocap_customer.vault_validator import (
    load_user_private_pem,
    validate_vault_structure,
)
from robocap_sdk.errors import ErrorCode, RobocapError


@dataclass
class _FakeCencMeta:
    customer_id: str
    cek_wrapped: bytes


def test_scan_cenc_mp4_only_includes_cenc_tagged(tmp_path: Path) -> None:
    cenc_mp4 = tmp_path / "encrypted.mp4"
    plain_mp4 = tmp_path / "plain.mp4"
    legacy = tmp_path / "legacy.mp4.enc"
    cenc_mp4.write_bytes(b"cenc")
    plain_mp4.write_bytes(b"plain")
    legacy.write_bytes(b"enc")

    with patch("robocap_customer.scanner.has_cenc_tags") as mock_has:
        mock_has.side_effect = lambda p: p.name == "encrypted.mp4"
        found = scan_cenc_mp4(tmp_path)

    assert [p.name for p in found] == ["encrypted.mp4"]


def test_scan_cenc_mp4_empty_for_missing_dir(tmp_path: Path) -> None:
    assert scan_cenc_mp4(tmp_path / "missing") == []


def test_validate_vault_structure_ok(customer_setup) -> None:
    validate_vault_structure(customer_setup["sdk_root"])


def test_load_user_private_pem(customer_setup, tmp_path: Path) -> None:
    pem_path = tmp_path / "user.pem"
    pem_path.write_bytes(customer_setup["private_pem"])
    pem = load_user_private_pem(pem_path)
    assert pem.startswith(b"-----BEGIN")


def test_preflight_cenc_mp4_ok(customer_setup, tmp_path: Path) -> None:
    mp4 = tmp_path / "clip.mp4"
    mp4.write_bytes(b"x")
    meta = _FakeCencMeta(
        customer_id=customer_setup["customer_id"],
        cek_wrapped=b"\x00" * 256,
    )

    with patch(
        "robocap_customer.preflight.load_cenc_metadata",
        return_value=meta,
    ), patch(
        "robocap_customer.preflight.verify_customer_private_key",
        return_value=None,
    ), patch(
        "robocap_customer.preflight.KeyVault.trial_unwrap_cek",
        return_value=object(),
    ):
        preflight_cenc_mp4(
            mp4,
            customer_setup["sdk_root"],
            customer_setup["private_pem"],
        )


def test_preflight_cenc_mp4_key_mismatch(customer_setup, tmp_path: Path) -> None:
    mp4 = tmp_path / "clip.mp4"
    mp4.write_bytes(b"x")
    meta = _FakeCencMeta(
        customer_id=customer_setup["customer_id"],
        cek_wrapped=b"\x00" * 256,
    )

    with patch(
        "robocap_customer.preflight.load_cenc_metadata",
        return_value=meta,
    ), patch(
        "robocap_customer.preflight.verify_customer_private_key",
        return_value=None,
    ), patch(
        "robocap_customer.preflight.KeyVault.trial_unwrap_cek",
        side_effect=RobocapError(
            ErrorCode.ERR_CENC_CEKA_TRIAL_FAILED,
            "trial failed",
        ),
    ):
        with pytest.raises(CustomerFacingError) as exc:
            preflight_cenc_mp4(
                mp4,
                customer_setup["sdk_root"],
                customer_setup["private_pem"],
            )
        assert exc.value.message == MSG_PREFLIGHT_KEY
