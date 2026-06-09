from __future__ import annotations

from pathlib import Path

from robocap_customer.key_bundle import (
    BundlePathKind,
    analyze_bundle_path,
    discover_child_bundles,
    is_valid_bundle_dir,
)
from tests.unit.test_customer_import import write_key_bundle
from tests.helpers import generate_rsa_keypair


def test_is_valid_bundle_dir(tmp_path: Path) -> None:
    pub, priv = generate_rsa_keypair(bits=2048)
    bundle = tmp_path / "b1"
    write_key_bundle(bundle, pub, priv)
    assert is_valid_bundle_dir(bundle)
    assert not is_valid_bundle_dir(tmp_path / "missing")


def test_discover_child_bundles_sorted(tmp_path: Path) -> None:
    pub, priv = generate_rsa_keypair(bits=2048)
    write_key_bundle(tmp_path / "z_last", pub, priv)
    write_key_bundle(tmp_path / "a_first", pub, priv)
    (tmp_path / "not_a_bundle").mkdir()
    (tmp_path / "readme.txt").write_text("x", encoding="utf-8")

    found = discover_child_bundles(tmp_path)
    assert [p.name for p in found] == ["a_first", "z_last"]


def test_analyze_direct_bundle(tmp_path: Path) -> None:
    pub, priv = generate_rsa_keypair(bits=2048)
    bundle = tmp_path / "direct"
    write_key_bundle(bundle, pub, priv)
    analysis = analyze_bundle_path(bundle)
    assert analysis.kind is BundlePathKind.DIRECT
    assert analysis.path == bundle.resolve()


def test_analyze_single_child(tmp_path: Path) -> None:
    pub, priv = generate_rsa_keypair(bits=2048)
    child = tmp_path / "only_child"
    write_key_bundle(child, pub, priv)
    analysis = analyze_bundle_path(tmp_path)
    assert analysis.kind is BundlePathKind.SINGLE_CHILD
    assert analysis.path == child.resolve()


def test_analyze_multiple_children(tmp_path: Path) -> None:
    pub, priv = generate_rsa_keypair(bits=2048)
    write_key_bundle(tmp_path / "v5", pub, priv)
    write_key_bundle(tmp_path / "v7", pub, priv)
    analysis = analyze_bundle_path(tmp_path)
    assert analysis.kind is BundlePathKind.MULTIPLE_CHILDREN
    assert len(analysis.candidates) == 2


def test_analyze_empty_directory(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    analysis = analyze_bundle_path(empty)
    assert analysis.kind is BundlePathKind.EMPTY


def test_analyze_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "new_dir"
    analysis = analyze_bundle_path(missing)
    assert analysis.kind is BundlePathKind.EMPTY
