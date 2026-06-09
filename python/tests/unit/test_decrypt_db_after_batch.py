from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from robocap_customer.batch_decryptor import BatchResult
from robocap_customer.conflict_resolver import FixedConflictResolver
from robocap_customer.prompts import SessionInput, run_decrypt_session


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

    failed_batch = BatchResult(total=1, succeeded=0, failed=1, skipped=0)

    with patch(
        "robocap_customer.prompts.scan_cenc_mp4",
        return_value=[input_root / "clip.mp4"],
    ), patch(
        "robocap_customer.prompts.preflight_cenc_mp4",
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

    ok_batch = BatchResult(total=1, succeeded=1, failed=0, skipped=0)

    with patch(
        "robocap_customer.prompts.scan_cenc_mp4",
        return_value=[input_root / "clip.mp4"],
    ), patch(
        "robocap_customer.prompts.preflight_cenc_mp4",
    ), patch(
        "robocap_customer.prompts.run_batch",
        return_value=ok_batch,
    ):
        run_decrypt_session(session, FixedConflictResolver("overwrite"))

    assert (output_root / "telemetry.db").read_bytes() == b"db-data"
