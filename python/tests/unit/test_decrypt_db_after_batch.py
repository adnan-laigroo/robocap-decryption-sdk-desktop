from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from robocap_customer.batch_decryptor import BatchResult
from robocap_customer.conflict_resolver import FixedConflictResolver
from robocap_customer.prompts import SessionInput, run_decrypt_session
from robocap_decryption_sdk.io.mp4_cenc import parse_cenc_metadata_from_tags
from tests.helpers_cenc import build_cenc_tag_payload


def test_run_decrypt_session_skips_db_copy_when_batch_failed(
    customer_setup, tmp_path: Path
) -> None:
    input_root = tmp_path / "in"
    output_root = tmp_path / "out"
    input_root.mkdir()
    output_root.mkdir()
    (input_root / "telemetry.db").write_bytes(b"db")

    session = SessionInput(
        vault_root=customer_setup["sdk_root"],
        user_private_key_path=tmp_path / "user.pem",
        input_root=input_root,
        output_root=output_root,
    )
    session.user_private_key_path.write_bytes(customer_setup["private_pem"])
    tags = build_cenc_tag_payload(
        customer_setup["public_pem"],
        customer_setup["private_pem"],
        customer_id=customer_setup["customer_id"],
    )
    meta = parse_cenc_metadata_from_tags(tags)

    failed_batch = BatchResult(total=1, succeeded=0, failed=1, skipped=0)

    with patch(
        "robocap_customer.prompts.scan_cenc_mp4",
        return_value=[input_root / "clip.mp4"],
    ), patch(
        "robocap_customer.prompts.load_cenc_metadata",
        return_value=meta,
    ), patch(
        "robocap_customer.prompts.preflight_cenc_metadata",
    ), patch(
        "robocap_customer.prompts.run_batch",
        return_value=failed_batch,
    ), patch(
        "robocap_customer.prompts.copy_plain_db_files",
    ) as mock_copy:
        run_decrypt_session(session, FixedConflictResolver("overwrite"))

    mock_copy.assert_not_called()
    assert not (output_root / "telemetry.db").exists()


def test_run_decrypt_session_copies_db_when_batch_succeeds(
    customer_setup, tmp_path: Path
) -> None:
    input_root = tmp_path / "in"
    output_root = tmp_path / "out"
    input_root.mkdir()
    output_root.mkdir()
    (input_root / "telemetry.db").write_bytes(b"db-data")

    session = SessionInput(
        vault_root=customer_setup["sdk_root"],
        user_private_key_path=tmp_path / "user.pem",
        input_root=input_root,
        output_root=output_root,
    )
    session.user_private_key_path.write_bytes(customer_setup["private_pem"])
    tags = build_cenc_tag_payload(
        customer_setup["public_pem"],
        customer_setup["private_pem"],
        customer_id=customer_setup["customer_id"],
    )
    meta = parse_cenc_metadata_from_tags(tags)

    ok_batch = BatchResult(total=1, succeeded=1, failed=0, skipped=0)

    with patch(
        "robocap_customer.prompts.scan_cenc_mp4",
        return_value=[input_root / "clip.mp4"],
    ), patch(
        "robocap_customer.prompts.load_cenc_metadata",
        return_value=meta,
    ), patch(
        "robocap_customer.prompts.preflight_cenc_metadata",
    ), patch(
        "robocap_customer.prompts.run_batch",
        return_value=ok_batch,
    ):
        run_decrypt_session(session, FixedConflictResolver("overwrite"))

    assert (output_root / "telemetry.db").read_bytes() == b"db-data"


def test_run_decrypt_session_reuses_loaded_metadata(customer_setup, tmp_path: Path) -> None:
    input_root = tmp_path / "in"
    output_root = tmp_path / "out"
    input_root.mkdir()
    output_root.mkdir()
    mp4 = input_root / "clip.mp4"
    mp4.write_bytes(b"video")

    session = SessionInput(
        vault_root=customer_setup["sdk_root"],
        user_private_key_path=tmp_path / "user.pem",
        input_root=input_root,
        output_root=output_root,
    )
    session.user_private_key_path.write_bytes(customer_setup["private_pem"])
    tags = build_cenc_tag_payload(
        customer_setup["public_pem"],
        customer_setup["private_pem"],
        customer_id=customer_setup["customer_id"],
    )

    with patch(
        "robocap_customer.prompts.scan_cenc_mp4",
        return_value=[mp4],
    ), patch(
        "robocap_customer.prompts.load_cenc_metadata"
    ) as mock_load_meta, patch(
        "robocap_customer.prompts.preflight_cenc_metadata"
    ), patch(
        "robocap_customer.prompts.run_batch",
        return_value=BatchResult(total=1, succeeded=1, failed=0, skipped=0),
    ) as mock_run_batch:
        mock_load_meta.return_value = parse_cenc_metadata_from_tags(tags)
        run_decrypt_session(session, FixedConflictResolver("overwrite"), max_workers=3)

    mock_load_meta.assert_called_once_with(mp4)
    assert mock_run_batch.call_count == 1
    kwargs = mock_run_batch.call_args.kwargs
    assert kwargs["max_workers"] == 3
    assert kwargs["metadata_by_path"][mp4] is mock_load_meta.return_value
