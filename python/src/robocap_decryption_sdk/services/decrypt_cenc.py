from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from robocap_decryption_sdk.auth.ownership import verify_customer_private_key
from robocap_decryption_sdk.config import DEFAULT_SDK_ROOT
from robocap_decryption_sdk.errors import ErrorCode, RobocapError
from robocap_decryption_sdk.io.ffmpeg_cli import decrypt_cenc_copy
from robocap_decryption_sdk.io.mp4_cenc import (
    CencMp4Metadata,
    load_cenc_metadata,
    verify_session_device_id_from_metadata,
)
from robocap_decryption_sdk.vault.key_vault import KeyVault
from robocap_decryption_sdk.vault.layout import ensure_private_dir

logger = logging.getLogger(__name__)


@dataclass
class DecryptCencResult:
    output_path: Path
    customer_id: str
    rsa_key_version: int
    kid_hex: str | None


def output_cenc_path(mp4_path: Path, output_dir: Path) -> Path:
    return output_dir / mp4_path.name


def decrypt_cenc_mp4(
    mp4_path: Path,
    user_private_pem: bytes,
    output_dir: Path,
    *,
    metadata: CencMp4Metadata | None = None,
    sdk_root: Path | None = None,
    session_device_id: str | None = None,
    ffprobe_executable: str | None = None,
    ffmpeg_executable: str | None = None,
) -> DecryptCencResult:
    meta = metadata or load_cenc_metadata(
        mp4_path,
        ffprobe_executable=ffprobe_executable,
    )
    if session_device_id is not None:
        verify_session_device_id_from_metadata(session_device_id, meta)

    root = sdk_root or DEFAULT_SDK_ROOT
    vault = KeyVault(root)

    if not vault.exists_customer(meta.customer_id):
        raise RobocapError(
            ErrorCode.ERR_CUSTOMER_NOT_FOUND,
            f"Customer not found in vault: {meta.customer_id}",
        )

    verified = verify_customer_private_key(
        meta.customer_id,
        user_private_pem,
        key_vault=vault,
    )
    logger.info(
        "Ownership verified for customer=%s matched_version=%s",
        meta.customer_id,
        verified.matched_rsa_key_version,
    )

    trial = vault.trial_unwrap_cek(meta.customer_id, meta.cek_wrapped)
    cek_hex = trial.cek.hex()

    ensure_private_dir(output_dir)
    out_path = output_cenc_path(mp4_path, output_dir)
    decrypt_cenc_copy(
        mp4_path,
        out_path,
        cek_hex,
        kid_hex=meta.kid_hex,
        ffmpeg_executable=ffmpeg_executable,
    )

    logger.info(
        "Decrypted cenc mp4=%s customer=%s rsa_version=%s output=%s",
        mp4_path,
        meta.customer_id,
        trial.rsa_key_version,
        out_path,
    )

    return DecryptCencResult(
        output_path=out_path,
        customer_id=meta.customer_id,
        rsa_key_version=trial.rsa_key_version,
        kid_hex=meta.kid_hex,
    )
