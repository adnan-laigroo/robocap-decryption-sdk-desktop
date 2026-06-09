from __future__ import annotations

from pathlib import Path

from robocap_sdk.auth.ownership import verify_customer_private_key
from robocap_sdk.errors import ErrorCode, RobocapError
from robocap_sdk.io.mp4_cenc import load_cenc_metadata
from robocap_sdk.vault.key_vault import KeyVault

from robocap_customer.error_mapper import (
    MSG_OWNERSHIP,
    MSG_PREFLIGHT_KEY,
    CustomerFacingError,
    to_message,
)


def preflight_cenc_mp4(
    mp4_path: Path,
    vault_root: Path,
    user_private_pem: bytes,
    *,
    ffprobe_executable: str | None = None,
) -> None:
    """Validate that a CENC file is likely to decrypt successfully."""
    root = vault_root.expanduser().resolve()
    mp4 = mp4_path.expanduser().resolve()

    try:
        meta = load_cenc_metadata(mp4, ffprobe_executable=ffprobe_executable)
    except RobocapError as exc:
        raise CustomerFacingError(to_message(exc)) from exc

    vault = KeyVault(root)
    if not vault.exists_customer(meta.customer_id):
        raise CustomerFacingError(MSG_OWNERSHIP)

    try:
        verify_customer_private_key(
            meta.customer_id,
            user_private_pem,
            key_vault=vault,
        )
    except RobocapError as exc:
        raise CustomerFacingError(to_message(exc)) from exc

    try:
        vault.trial_unwrap_cek(meta.customer_id, meta.cek_wrapped)
    except RobocapError as exc:
        if exc.code == ErrorCode.ERR_CENC_CEKA_TRIAL_FAILED:
            raise CustomerFacingError(MSG_PREFLIGHT_KEY) from exc
        raise CustomerFacingError(to_message(exc)) from exc
