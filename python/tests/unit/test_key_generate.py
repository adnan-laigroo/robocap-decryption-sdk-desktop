from __future__ import annotations

from pathlib import Path

from robocap_customer.key_bundle import (
    PRIVATE_PEM_NAME,
    PUBLIC_PEM_NAME,
    USER_PRIVATE_PEM_NAME,
    is_valid_bundle_dir,
    load_key_bundle,
)
from robocap_customer.key_generate import generate_cenc_key_bundle


def test_generate_cenc_key_bundle_writes_files(tmp_path: Path) -> None:
    out = generate_cenc_key_bundle(tmp_path / "gen", include_user_private=True)
    assert is_valid_bundle_dir(out)
    assert (out / USER_PRIVATE_PEM_NAME).is_file()
    bundle = load_key_bundle(out)
    assert bundle.public_pem
    assert bundle.private_pem


def test_generate_without_user_private(tmp_path: Path) -> None:
    out = generate_cenc_key_bundle(tmp_path / "gen", include_user_private=False)
    assert (out / PUBLIC_PEM_NAME).is_file()
    assert (out / PRIVATE_PEM_NAME).is_file()
    assert not (out / USER_PRIVATE_PEM_NAME).exists()
