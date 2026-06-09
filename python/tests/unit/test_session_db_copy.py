from __future__ import annotations

from pathlib import Path

import pytest

from robocap_customer.conflict_resolver import FixedConflictResolver
from robocap_customer.error_mapper import MSG_DB_COPY_FAILED, CustomerFacingError
from robocap_customer.session_files import (
    copy_plain_db_files,
    scan_plain_db_files,
)


def test_scan_plain_db_excludes_enc_suffix(tmp_path: Path) -> None:
    (tmp_path / "a.db").write_bytes(b"plain")
    (tmp_path / "b.db.enc").write_bytes(b"enc")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.db").write_bytes(b"nested")

    found = scan_plain_db_files(tmp_path)
    names = {p.name for p in found}
    assert names == {"a.db", "c.db"}


def test_copy_plain_db_preserves_relative_paths(tmp_path: Path) -> None:
    input_root = tmp_path / "session"
    output_root = tmp_path / "out"
    input_root.mkdir()
    (input_root / "top.db").write_bytes(b"1")
    sub = input_root / "nested"
    sub.mkdir()
    (sub / "inner.db").write_bytes(b"2")

    result = copy_plain_db_files(
        scan_plain_db_files(input_root),
        input_root=input_root,
        output_root=output_root,
        conflict_resolver=FixedConflictResolver("overwrite"),
    )

    assert result.total == 2
    assert result.copied == 2
    assert result.skipped == 0
    assert (output_root / "top.db").read_bytes() == b"1"
    assert (output_root / "nested" / "inner.db").read_bytes() == b"2"


def test_copy_plain_db_skip_on_conflict(tmp_path: Path) -> None:
    input_root = tmp_path / "session"
    output_root = tmp_path / "out"
    input_root.mkdir()
    (input_root / "clip.db").write_bytes(b"new")
    output_root.mkdir(parents=True)
    (output_root / "clip.db").write_bytes(b"old")

    result = copy_plain_db_files(
        [input_root / "clip.db"],
        input_root=input_root,
        output_root=output_root,
        conflict_resolver=FixedConflictResolver("skip"),
    )

    assert result.copied == 0
    assert result.skipped == 1
    assert (output_root / "clip.db").read_bytes() == b"old"


def test_copy_plain_db_raises_customer_facing_on_permission_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_root = tmp_path / "session"
    output_root = tmp_path / "out"
    input_root.mkdir()
    (input_root / "clip.db").write_bytes(b"x")

    def fail_copy(*_args, **_kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr("robocap_customer.session_files.shutil.copy2", fail_copy)

    with pytest.raises(CustomerFacingError) as exc_info:
        copy_plain_db_files(
            [input_root / "clip.db"],
            input_root=input_root,
            output_root=output_root,
            conflict_resolver=FixedConflictResolver("overwrite"),
        )
    assert "writable" in exc_info.value.message.lower()


def test_copy_plain_db_generic_failure_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_root = tmp_path / "session"
    output_root = tmp_path / "out"
    input_root.mkdir()
    (input_root / "clip.db").write_bytes(b"x")

    def fail_copy(*_args, **_kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr("robocap_customer.session_files.shutil.copy2", fail_copy)

    with pytest.raises(CustomerFacingError) as exc_info:
        copy_plain_db_files(
            [input_root / "clip.db"],
            input_root=input_root,
            output_root=output_root,
            conflict_resolver=FixedConflictResolver("overwrite"),
        )
    assert exc_info.value.message == MSG_DB_COPY_FAILED
