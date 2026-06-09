from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from robocap_customer.error_mapper import MSG_GEN_CANCELLED
from robocap_customer.import_prompts import _resolve_key_bundle_directory
from tests.unit.test_customer_import import write_key_bundle
from tests.helpers import generate_rsa_keypair


def test_resolve_creates_and_generates(tmp_path: Path) -> None:
    target = tmp_path / "new_bundle"
    with patch("robocap_customer.import_prompts._prompt_yes_no", return_value=True):
        resolved = _resolve_key_bundle_directory(target)
    assert resolved == target.resolve()
    assert (resolved / "rsa_public_spki.pem").is_file()


def test_resolve_direct_bundle(tmp_path: Path) -> None:
    pub, priv = generate_rsa_keypair(bits=2048)
    bundle = tmp_path / "direct"
    write_key_bundle(bundle, pub, priv)
    resolved = _resolve_key_bundle_directory(bundle)
    assert resolved == bundle.resolve()


def test_resolve_picks_among_children(tmp_path: Path) -> None:
    pub, priv = generate_rsa_keypair(bits=2048)
    v5 = tmp_path / "v5"
    v7 = tmp_path / "v7"
    write_key_bundle(v5, pub, priv)
    write_key_bundle(v7, pub, priv)
    with patch("robocap_customer.import_prompts.input", return_value="2"):
        resolved = _resolve_key_bundle_directory(tmp_path)
    assert resolved == v7.resolve()


def test_resolve_generate_cancelled(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with patch("robocap_customer.import_prompts._prompt_yes_no", return_value=False):
        with pytest.raises(Exception) as exc_info:
            _resolve_key_bundle_directory(empty)
    assert exc_info.value.message == MSG_GEN_CANCELLED
