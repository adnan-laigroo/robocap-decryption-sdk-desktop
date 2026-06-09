from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from robocap_sdk.errors import ErrorCode, RobocapError
from robocap_sdk.config import RSA_2048_CIPHERTEXT_BYTES
from robocap_sdk.io.mp4_cenc import (
    has_cenc_tags,
    load_cenc_metadata,
    parse_cenc_metadata_from_tags,
    read_format_tags,
)
from robocap_sdk.services.decrypt_cenc import decrypt_cenc_mp4
from robocap_sdk.vault.key_vault import KeyVault
from tests.helpers import generate_rsa_keypair
from tests.helpers_cenc import (
    EMBEDDED_CENC_PRIVATE_PEM,
    EMBEDDED_CENC_PUBLIC_PEM,
    build_cenc_tag_payload,
    import_cenc_rsa_v1,
    import_cenc_rsa_vN,
)


def _ffprobe_result(tags: dict[str, str]):
    payload = {"format": {"tags": tags}}

    class Result:
        returncode = 0
        stdout = json.dumps(payload).encode("utf-8")
        stderr = b""

    return Result()


def _mock_ffprobe(tags: dict[str, str]):
    return patch(
        "robocap_sdk.io.mp4_cenc.resolve_ffprobe_executable",
        return_value="ffprobe",
    ), patch(
        "robocap_sdk.io.mp4_cenc.subprocess.run",
        return_value=_ffprobe_result(tags),
    )


def test_read_format_tags_parses_ffprobe_json(tmp_path):
    mp4 = tmp_path / "sample.mp4"
    mp4.write_bytes(b"fake")
    tags = build_cenc_tag_payload(
        EMBEDDED_CENC_PUBLIC_PEM,
        EMBEDDED_CENC_PRIVATE_PEM,
        customer_id="CENC_CUST",
    )

    ffprobe_patch, run_patch = _mock_ffprobe(tags)
    with ffprobe_patch, run_patch:
        parsed = read_format_tags(mp4)

    assert parsed["cenc_customer_id"] == "CENC_CUST"


def test_parse_cenc_metadata_minimal_tags():
    public_pem, private_pem = generate_rsa_keypair(bits=2048)
    tags = build_cenc_tag_payload(public_pem, private_pem, customer_id="CENC_CUST")
    meta = parse_cenc_metadata_from_tags(tags)
    assert meta.customer_id == "CENC_CUST"
    assert len(meta.cek_wrapped) == RSA_2048_CIPHERTEXT_BYTES


def test_parse_missing_customer_id():
    public_pem, private_pem = generate_rsa_keypair(bits=2048)
    tags = build_cenc_tag_payload(public_pem, private_pem)
    del tags["cenc_customer_id"]
    with pytest.raises(RobocapError) as exc:
        parse_cenc_metadata_from_tags(tags)
    assert exc.value.code == ErrorCode.ERR_CENC_TAGS_MISSING


def test_parse_customer_id_from_username_fallback():
    public_pem, private_pem = generate_rsa_keypair(bits=2048)
    tags = build_cenc_tag_payload(public_pem, private_pem, customer_id="CENC_CUST")
    del tags["cenc_customer_id"]
    tags["username"] = "frodobot"
    meta = parse_cenc_metadata_from_tags(tags)
    assert meta.customer_id == "frodobot"


def test_parse_prefers_cenc_customer_id_over_username():
    public_pem, private_pem = generate_rsa_keypair(bits=2048)
    tags = build_cenc_tag_payload(public_pem, private_pem, customer_id="PRIMARY_ID")
    tags["username"] = "frodobot"
    meta = parse_cenc_metadata_from_tags(tags)
    assert meta.customer_id == "PRIMARY_ID"


def test_parse_invalid_customer_id():
    public_pem, private_pem = generate_rsa_keypair(bits=2048)
    tags = build_cenc_tag_payload(public_pem, private_pem, customer_id="bad id")
    with pytest.raises(RobocapError) as exc:
        parse_cenc_metadata_from_tags(tags)
    assert exc.value.code == ErrorCode.ERR_CENC_CUSTOMER_ID_INVALID


def test_parse_invalid_base64():
    public_pem, private_pem = generate_rsa_keypair(bits=2048)
    tags = build_cenc_tag_payload(public_pem, private_pem)
    tags["cenc_cek_wrapped_b64"] = "not-valid-base64!!"
    with pytest.raises(RobocapError) as exc:
        parse_cenc_metadata_from_tags(tags)
    assert exc.value.code == ErrorCode.ERR_CENC_TAGS_MISSING


def test_parse_wrapped_length():
    public_pem, private_pem = generate_rsa_keypair(bits=2048)
    tags = build_cenc_tag_payload(public_pem, private_pem)
    tags["cenc_cek_wrapped_b64"] = "AA=="
    with pytest.raises(RobocapError) as exc:
        parse_cenc_metadata_from_tags(tags)
    assert exc.value.code == ErrorCode.ERR_CENC_CEKA_WRAP


def test_has_cenc_tags_accepts_username_fallback(tmp_path):
    mp4 = tmp_path / "clip.mp4"
    mp4.write_bytes(b"x")
    tags = {
        "cenc_cek_wrapped_b64": "abc",
        "username": "frodobot",
    }

    ffprobe_patch, run_patch = _mock_ffprobe(tags)
    with ffprobe_patch, run_patch:
        assert has_cenc_tags(mp4) is True


def test_has_cenc_tags_requires_customer_source(tmp_path):
    mp4 = tmp_path / "clip.mp4"
    mp4.write_bytes(b"x")
    only_cek = {"cenc_cek_wrapped_b64": "abc"}

    ffprobe_patch, run_patch = _mock_ffprobe(only_cek)
    with ffprobe_patch, run_patch:
        assert has_cenc_tags(mp4) is False


def test_load_cenc_metadata_roundtrip(tmp_path):
    mp4 = tmp_path / "video.mp4"
    mp4.write_bytes(b"fake")
    public_pem, private_pem = generate_rsa_keypair(bits=2048)
    tags = build_cenc_tag_payload(public_pem, private_pem, customer_id="CENC_CUST")

    ffprobe_patch, run_patch = _mock_ffprobe(tags)
    with ffprobe_patch, run_patch:
        meta = load_cenc_metadata(mp4)

    assert meta.customer_id == "CENC_CUST"
    assert len(meta.cek_wrapped) == RSA_2048_CIPHERTEXT_BYTES


def _decrypt_with_mocks(
    mp4: Path,
    out_dir: Path,
    sdk_root: Path,
    tags: dict[str, str],
    user_pem: bytes,
):
    meta = parse_cenc_metadata_from_tags(tags)

    class FfmpegResult:
        returncode = 0
        stdout = b""
        stderr = b""

    with patch(
        "robocap_sdk.services.decrypt_cenc.load_cenc_metadata",
        return_value=meta,
    ), patch(
        "robocap_sdk.io.ffmpeg_cli.resolve_ffmpeg_executable",
        return_value="ffmpeg",
    ), patch(
        "robocap_sdk.io.ffmpeg_cli.subprocess.run",
        return_value=FfmpegResult(),
    ):
        return decrypt_cenc_mp4(
            mp4,
            user_pem,
            out_dir,
            sdk_root=sdk_root,
            ffmpeg_executable="ffmpeg",
        )


def test_decrypt_cenc_mp4_mocked(sdk_root, tmp_path):
    customer_id = "CENC_CUST"
    import_cenc_rsa_v1(
        sdk_root,
        customer_id,
        EMBEDDED_CENC_PUBLIC_PEM,
        EMBEDDED_CENC_PRIVATE_PEM,
    )

    mp4 = tmp_path / "segment.mp4"
    mp4.write_bytes(b"encrypted")
    out_dir = tmp_path / "out"
    tags = build_cenc_tag_payload(
        EMBEDDED_CENC_PUBLIC_PEM,
        EMBEDDED_CENC_PRIVATE_PEM,
        customer_id=customer_id,
    )

    result = _decrypt_with_mocks(
        mp4,
        out_dir,
        sdk_root,
        tags,
        EMBEDDED_CENC_PRIVATE_PEM,
    )

    assert result.output_path == out_dir / "segment.mp4"
    assert result.customer_id == customer_id
    assert result.rsa_key_version == 1


def test_decrypt_hits_v2_when_wrapped_with_v2(sdk_root, tmp_path):
    customer_id = "CENC_CUST"
    pub_v1, priv_v1 = generate_rsa_keypair(bits=2048)
    pub_v2, priv_v2 = generate_rsa_keypair(bits=2048)
    import_cenc_rsa_vN(sdk_root, customer_id, pub_v1, priv_v1, 1)
    import_cenc_rsa_vN(sdk_root, customer_id, pub_v2, priv_v2, 2)

    mp4 = tmp_path / "segment.mp4"
    mp4.write_bytes(b"encrypted")
    out_dir = tmp_path / "out"
    tags = build_cenc_tag_payload(pub_v2, priv_v2, customer_id=customer_id)

    result = _decrypt_with_mocks(
        mp4,
        out_dir,
        sdk_root,
        tags,
        priv_v1,
    )

    assert result.rsa_key_version == 2
    assert result.customer_id == customer_id


def test_decrypt_trial_failed_missing_v1(sdk_root, tmp_path):
    customer_id = "CENC_CUST"
    pub_v1, priv_v1 = generate_rsa_keypair(bits=2048)
    pub_v2, priv_v2 = generate_rsa_keypair(bits=2048)
    import_cenc_rsa_vN(sdk_root, customer_id, pub_v2, priv_v2, 2)

    mp4 = tmp_path / "segment.mp4"
    mp4.write_bytes(b"encrypted")
    out_dir = tmp_path / "out"
    tags = build_cenc_tag_payload(pub_v1, priv_v1, customer_id=customer_id)

    with pytest.raises(RobocapError) as exc:
        _decrypt_with_mocks(
            mp4,
            out_dir,
            sdk_root,
            tags,
            priv_v2,
        )
    assert exc.value.code == ErrorCode.ERR_CENC_CEKA_TRIAL_FAILED


def test_decrypt_customer_not_in_vault(sdk_root, tmp_path):
    customer_id = "CENC_CUST"
    import_cenc_rsa_v1(
        sdk_root,
        customer_id,
        EMBEDDED_CENC_PUBLIC_PEM,
        EMBEDDED_CENC_PRIVATE_PEM,
    )

    mp4 = tmp_path / "segment.mp4"
    mp4.write_bytes(b"encrypted")
    out_dir = tmp_path / "out"
    tags = build_cenc_tag_payload(
        EMBEDDED_CENC_PUBLIC_PEM,
        EMBEDDED_CENC_PRIVATE_PEM,
        customer_id="OTHER_CUST",
    )

    with pytest.raises(RobocapError) as exc:
        _decrypt_with_mocks(
            mp4,
            out_dir,
            sdk_root,
            tags,
            EMBEDDED_CENC_PRIVATE_PEM,
        )
    assert exc.value.code == ErrorCode.ERR_CUSTOMER_NOT_FOUND


def test_old_three_tag_payload_fails():
    public_pem, private_pem = generate_rsa_keypair(bits=2048)
    tags = {
        "cenc_cek_wrapped_b64": build_cenc_tag_payload(public_pem, private_pem)[
            "cenc_cek_wrapped_b64"
        ],
        "cenc_rsa_public_key_pem": public_pem.decode("utf-8"),
        "cenc_wrapped_algo": "rsa-oaep-sha256",
    }
    with pytest.raises(RobocapError) as exc:
        parse_cenc_metadata_from_tags(tags)
    assert exc.value.code == ErrorCode.ERR_CENC_TAGS_MISSING
