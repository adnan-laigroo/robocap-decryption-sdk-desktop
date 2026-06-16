from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from robocap_decryption_sdk.config import FFMPEG_ENV_VAR, FFPROBE_ENV_VAR
from robocap_decryption_sdk.errors import ErrorCode, RobocapError


def resolve_ffprobe_executable(explicit: str | None = None) -> str:
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return str(path)
        if "/" not in explicit and "\\" not in explicit:
            return explicit
        raise RobocapError(
            ErrorCode.ERR_FFPROBE_NOT_FOUND,
            f"ffprobe executable not found: {explicit}",
        )
    env_path = os.environ.get(FFPROBE_ENV_VAR)
    if env_path and Path(env_path).is_file():
        return env_path
    ffmpeg_env = os.environ.get(FFMPEG_ENV_VAR)
    if ffmpeg_env:
        ffmpeg_path = Path(ffmpeg_env)
        if ffmpeg_path.is_file():
            sibling = ffmpeg_path.with_name(
                "ffprobe.exe" if ffmpeg_path.suffix.lower() == ".exe" else "ffprobe"
            )
            if sibling.is_file():
                return str(sibling)
    found = shutil.which("ffprobe")
    if found:
        return found
    raise RobocapError(
        ErrorCode.ERR_FFPROBE_NOT_FOUND,
        "ffprobe executable not found in PATH",
    )


def resolve_ffmpeg_executable(explicit: str | None = None) -> str:
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return str(path)
        if "/" not in explicit and "\\" not in explicit:
            return explicit
        raise RobocapError(
            ErrorCode.ERR_FFMPEG_NOT_FOUND,
            f"ffmpeg executable not found: {explicit}",
        )
    env_path = os.environ.get(FFMPEG_ENV_VAR)
    if env_path and Path(env_path).is_file():
        return env_path
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise RobocapError(
        ErrorCode.ERR_FFMPEG_NOT_FOUND,
        "ffmpeg executable not found in PATH",
    )


def decrypt_cenc_copy(
    input_mp4: Path,
    output_mp4: Path,
    cek_hex: str,
    *,
    kid_hex: str | None = None,
    ffmpeg_executable: str | None = None,
) -> None:
    exe = resolve_ffmpeg_executable(ffmpeg_executable)
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        exe,
        "-y",
        "-decryption_key",
        cek_hex,
    ]
    if kid_hex:
        cmd.extend(["-decryption_kid", kid_hex])
    cmd.extend(
        [
            "-i",
            str(input_mp4),
            "-map",
            "0",
            "-map_metadata",
            "0",
            "-c",
            "copy",
            "-movflags",
            "+use_metadata_tags",
        ]
    )
    from robocap_decryption_sdk.io.mp4_cenc import CENC_STRIP_TAGS_ON_DECRYPT

    for tag in CENC_STRIP_TAGS_ON_DECRYPT:
        cmd.extend(["-metadata", f"{tag}="])
    cmd.append(str(output_mp4))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            check=False,
            timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RobocapError(
            ErrorCode.ERR_CENC_DECRYPT_FAILED,
            "ffmpeg CENC decrypt subprocess failed",
        ) from exc

    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        raise RobocapError(
            ErrorCode.ERR_CENC_DECRYPT_FAILED,
            f"ffmpeg CENC decrypt failed: {stderr}",
        )
