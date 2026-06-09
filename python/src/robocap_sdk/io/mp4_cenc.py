from __future__ import annotations

import base64
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from robocap_sdk.config import RSA_2048_CIPHERTEXT_BYTES, validate_customer_id
from robocap_sdk.errors import ErrorCode, RobocapError
from robocap_sdk.io.ffmpeg_cli import resolve_ffprobe_executable

_CEKA_TAG = "cenc_cek_wrapped_b64"
_CENC_WRAPPED_ALGO_TAG = "cenc_wrapped_algo"
_CUSTOMER_ID_TAG = "cenc_customer_id"
_CUSTOMER_ID_FALLBACK_TAG = "username"

CENC_STRIP_TAGS_ON_DECRYPT = (
    _CEKA_TAG,
    _CENC_WRAPPED_ALGO_TAG,
)


@dataclass(frozen=True)
class CencMp4Metadata:
    customer_id: str
    cek_wrapped: bytes
    kid_hex: str | None


def _parse_ffprobe_json(raw: str) -> dict:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RobocapError(
            ErrorCode.ERR_CENC_FFPROBE_FAILED,
            "ffprobe returned invalid JSON",
        ) from exc
    if not isinstance(payload, dict):
        raise RobocapError(
            ErrorCode.ERR_CENC_FFPROBE_FAILED,
            "ffprobe JSON root must be an object",
        )
    return payload


def read_format_tags(
    mp4_path: Path,
    *,
    ffprobe_executable: str | None = None,
) -> dict[str, str]:
    mp4_path = mp4_path.expanduser().resolve()
    if not mp4_path.is_file():
        raise RobocapError(
            ErrorCode.ERR_CENC_TAGS_MISSING,
            f"MP4 file not found: {mp4_path}",
        )

    exe = resolve_ffprobe_executable(ffprobe_executable)
    cmd = [
        exe,
        "-v",
        "error",
        "-show_format",
        "-print_format",
        "json",
        str(mp4_path),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RobocapError(
            ErrorCode.ERR_CENC_FFPROBE_FAILED,
            "ffprobe subprocess failed",
        ) from exc

    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        raise RobocapError(
            ErrorCode.ERR_CENC_FFPROBE_FAILED,
            f"ffprobe failed: {stderr}",
        )

    payload = _parse_ffprobe_json(result.stdout.decode("utf-8"))
    fmt = payload.get("format")
    if not isinstance(fmt, dict):
        raise RobocapError(
            ErrorCode.ERR_CENC_TAGS_MISSING,
            "ffprobe output missing format section",
        )
    tags = fmt.get("tags")
    if not isinstance(tags, dict):
        raise RobocapError(
            ErrorCode.ERR_CENC_TAGS_MISSING,
            "MP4 has no format metadata tags",
        )
    return {str(key): str(value) for key, value in tags.items()}


def _resolve_customer_id(tags: dict[str, str]) -> str:
    raw = tags.get(_CUSTOMER_ID_TAG) or tags.get(_CUSTOMER_ID_FALLBACK_TAG)
    if not raw or not raw.strip():
        raise RobocapError(
            ErrorCode.ERR_CENC_TAGS_MISSING,
            f"Missing CENC customer id: {_CUSTOMER_ID_TAG} or {_CUSTOMER_ID_FALLBACK_TAG} tag required",
        )
    customer_id = raw.strip()
    try:
        validate_customer_id(customer_id)
    except ValueError as exc:
        raise RobocapError(
            ErrorCode.ERR_CENC_CUSTOMER_ID_INVALID,
            f"Invalid customer id: {customer_id!r}",
        ) from exc
    return customer_id


def _has_customer_id_source(tags: dict[str, str]) -> bool:
    for key in (_CUSTOMER_ID_TAG, _CUSTOMER_ID_FALLBACK_TAG):
        value = tags.get(key)
        if value and value.strip():
            return True
    return False


def parse_cenc_metadata_from_tags(tags: dict[str, str]) -> CencMp4Metadata:
    if not tags.get(_CEKA_TAG):
        raise RobocapError(
            ErrorCode.ERR_CENC_TAGS_MISSING,
            f"Missing CENC tags: {_CEKA_TAG}",
        )

    customer_id = _resolve_customer_id(tags)

    try:
        cek_wrapped = base64.b64decode(tags[_CEKA_TAG], validate=True)
    except Exception as exc:
        raise RobocapError(
            ErrorCode.ERR_CENC_TAGS_MISSING,
            "Invalid cenc_cek_wrapped_b64 Base64",
        ) from exc

    if len(cek_wrapped) != RSA_2048_CIPHERTEXT_BYTES:
        raise RobocapError(
            ErrorCode.ERR_CENC_CEKA_WRAP,
            f"Wrapped CEK must be {RSA_2048_CIPHERTEXT_BYTES} bytes",
        )

    kid_hex = tags.get("cenc_kid_hex")
    if kid_hex is not None:
        kid_hex = kid_hex.strip().lower() or None

    return CencMp4Metadata(
        customer_id=customer_id,
        cek_wrapped=cek_wrapped,
        kid_hex=kid_hex,
    )


def load_cenc_metadata(
    mp4_path: Path,
    *,
    ffprobe_executable: str | None = None,
) -> CencMp4Metadata:
    tags = read_format_tags(mp4_path, ffprobe_executable=ffprobe_executable)
    return parse_cenc_metadata_from_tags(tags)


def has_cenc_tags(
    mp4_path: Path,
    *,
    ffprobe_executable: str | None = None,
) -> bool:
    try:
        tags = read_format_tags(mp4_path, ffprobe_executable=ffprobe_executable)
    except RobocapError:
        return False
    return bool(tags.get(_CEKA_TAG)) and _has_customer_id_source(tags)
