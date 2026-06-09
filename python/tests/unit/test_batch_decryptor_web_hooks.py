from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from robocap_customer.batch_decryptor import run_batch
from robocap_customer.conflict_resolver import FixedConflictResolver


def test_run_batch_progress_fn_called(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    input_root = tmp_path / "in"
    output_root = tmp_path / "out"
    input_root.mkdir()
    output_root.mkdir()
    mp4 = input_root / "clip.mp4"
    mp4.write_bytes(b"x")

    calls: list[tuple[int, int, str]] = []

    def progress_fn(current: int, total: int, msg: str) -> None:
        calls.append((current, total, msg))

    with patch("robocap_customer.batch_decryptor.decrypt_cenc_mp4") as mock_decrypt:
        mock_decrypt.return_value = tmp_path / "out" / "clip.mp4"
        result = run_batch(
            [mp4],
            vault_root=vault,
            private_pem=b"pem",
            input_root=input_root,
            output_root=output_root,
            conflict_resolver=FixedConflictResolver("overwrite"),
            progress_fn=progress_fn,
        )

    assert result.succeeded == 1
    assert any(c[0] == 1 and c[1] == 1 for c in calls)


def test_run_batch_cancel_check_stops_early(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    input_root = tmp_path / "in"
    output_root = tmp_path / "out"
    input_root.mkdir()
    output_root.mkdir()
    first = input_root / "a.mp4"
    second = input_root / "b.mp4"
    first.write_bytes(b"a")
    second.write_bytes(b"b")

    seen: list[str] = []

    def cancel_check() -> bool:
        return len(seen) >= 1

    with patch("robocap_customer.batch_decryptor.decrypt_cenc_mp4") as mock_decrypt:
        def _decrypt(mp4_path: Path, *args, **kwargs):
            seen.append(mp4_path.name)
            return output_root / mp4_path.name

        mock_decrypt.side_effect = _decrypt
        result = run_batch(
            [first, second],
            vault_root=vault,
            private_pem=b"pem",
            input_root=input_root,
            output_root=output_root,
            conflict_resolver=FixedConflictResolver("overwrite"),
            cancel_check=cancel_check,
        )

    assert result.succeeded == 1
    assert seen == ["a.mp4"]
