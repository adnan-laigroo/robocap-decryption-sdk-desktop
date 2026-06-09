from __future__ import annotations

from pathlib import Path

from robocap_customer.key_bundle import (
    PRIVATE_PEM_NAME,
    PUBLIC_PEM_NAME,
    next_version_subdir_name,
    resolve_key_generate_dir,
)


def test_next_version_subdir_name(tmp_path: Path) -> None:
    assert next_version_subdir_name(tmp_path) == "v1"
    (tmp_path / "v1").mkdir()
    assert next_version_subdir_name(tmp_path) == "v2"
    (tmp_path / "v2").mkdir()
    assert next_version_subdir_name(tmp_path) == "v3"


def test_resolve_key_generate_dir_subfolder(tmp_path: Path) -> None:
    target = resolve_key_generate_dir(tmp_path / "keys", "subfolder")
    assert target.name == "v1"
    assert target.is_dir()


def test_resolve_key_generate_dir_direct(tmp_path: Path) -> None:
    parent = tmp_path / "keys"
    target = resolve_key_generate_dir(parent, "direct")
    assert target == parent.resolve()
