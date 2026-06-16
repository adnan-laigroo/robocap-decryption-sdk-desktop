from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from robocap_decryption_sdk.errors import ErrorCode, RobocapError
from robocap_decryption_sdk.io.ffmpeg_cli import decrypt_cenc_copy


def _mock_run_success(*args, **kwargs):
    class _Result:
        returncode = 0
        stderr = b""

    return _Result()


def test_decrypt_cenc_copy_preserves_metadata_flags(tmp_path: Path) -> None:
    input_mp4 = tmp_path / "in.mp4"
    output_mp4 = tmp_path / "out.mp4"
    input_mp4.write_bytes(b"fake")

    captured: dict[str, list] = {}

    def _capture_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _mock_run_success()

    with patch(
        "robocap_decryption_sdk.io.ffmpeg_cli.resolve_ffmpeg_executable",
        return_value="ffmpeg",
    ), patch(
        "robocap_decryption_sdk.io.ffmpeg_cli.subprocess.run",
        side_effect=_capture_run,
    ):
        decrypt_cenc_copy(
            input_mp4,
            output_mp4,
            "00" * 16,
            kid_hex="ab" * 16,
            ffmpeg_executable="ffmpeg",
        )

    cmd = captured["cmd"]
    assert cmd[0] == "ffmpeg"
    assert "-decryption_key" in cmd
    assert "-decryption_kid" in cmd
    assert "-map" in cmd
    assert cmd[cmd.index("-map") + 1] == "0"
    assert "-map_metadata" in cmd
    assert cmd[cmd.index("-map_metadata") + 1] == "0"
    assert "-c" in cmd
    assert cmd[cmd.index("-c") + 1] == "copy"
    assert "-movflags" in cmd
    assert cmd[cmd.index("-movflags") + 1] == "+use_metadata_tags"
    assert "-metadata" in cmd
    assert "cenc_cek_wrapped_b64=" in cmd
    assert "cenc_wrapped_algo=" in cmd
    assert str(output_mp4) == cmd[-1]


def test_decrypt_cenc_copy_omits_kid_when_not_provided(tmp_path: Path) -> None:
    input_mp4 = tmp_path / "in.mp4"
    output_mp4 = tmp_path / "out.mp4"
    input_mp4.write_bytes(b"fake")

    captured: dict[str, list] = {}

    def _capture_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _mock_run_success()

    with patch(
        "robocap_decryption_sdk.io.ffmpeg_cli.resolve_ffmpeg_executable",
        return_value="ffmpeg",
    ), patch(
        "robocap_decryption_sdk.io.ffmpeg_cli.subprocess.run",
        side_effect=_capture_run,
    ):
        decrypt_cenc_copy(
            input_mp4,
            output_mp4,
            "00" * 16,
            ffmpeg_executable="ffmpeg",
        )

    assert "-decryption_kid" not in captured["cmd"]


def test_decrypt_cenc_copy_raises_on_ffmpeg_failure(tmp_path: Path) -> None:
    input_mp4 = tmp_path / "in.mp4"
    output_mp4 = tmp_path / "out.mp4"
    input_mp4.write_bytes(b"fake")

    class _FailResult:
        returncode = 1
        stderr = b"decode error"

    with patch(
        "robocap_decryption_sdk.io.ffmpeg_cli.resolve_ffmpeg_executable",
        return_value="ffmpeg",
    ), patch(
        "robocap_decryption_sdk.io.ffmpeg_cli.subprocess.run",
        return_value=_FailResult(),
    ):
        with pytest.raises(RobocapError) as exc_info:
            decrypt_cenc_copy(
                input_mp4,
                output_mp4,
                "00" * 16,
                ffmpeg_executable="ffmpeg",
            )
    assert exc_info.value.code == ErrorCode.ERR_CENC_DECRYPT_FAILED
