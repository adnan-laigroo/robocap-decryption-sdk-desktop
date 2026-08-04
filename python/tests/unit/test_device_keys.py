from __future__ import annotations

import json
from pathlib import Path

import pytest

from robocap_customer.device_keys import (
    USER_PRIVATE_INDEX_NAME,
    load_user_private_index,
    register_user_private_version,
    remove_user_private_version_from_index,
    resolve_user_private_key,
    save_user_private_index,
    user_private_index_path,
    vault_user_private_path,
    vault_user_private_path_for_version,
    UserPrivateIndex,
)
from robocap_customer.error_mapper import CustomerFacingError, MSG_DEVICE_PRIVATE_KEY_MISSING
from robocap_customer.key_bundle import USER_PRIVATE_PEM_NAME


def test_vault_user_private_path(tmp_path: Path) -> None:
    path = vault_user_private_path(tmp_path / "vault", "d38abc4c26cf1e23")
    assert path == tmp_path / "vault" / "vault" / "keys" / "d38abc4c26cf1e23" / "user_private.pem"


def test_vault_user_private_path_for_version(tmp_path: Path) -> None:
    path = vault_user_private_path_for_version(tmp_path / "vault", "dev1", 2)
    assert path == (
        tmp_path / "vault" / "vault" / "keys" / "dev1" / "rsa" / "v2" / USER_PRIVATE_PEM_NAME
    )


def test_user_private_index_roundtrip(tmp_path: Path) -> None:
    index = UserPrivateIndex(
        device_id="dev1",
        active_version=2,
        versions={"1": "rsa/v1/user_private.pem", "2": "rsa/v2/user_private.pem"},
    )
    save_user_private_index(tmp_path / "vault", index)
    loaded = load_user_private_index(tmp_path / "vault", "dev1")
    assert loaded is not None
    assert loaded.device_id == "dev1"
    assert loaded.active_version == 2
    assert loaded.versions["2"] == "rsa/v2/user_private.pem"
    assert user_private_index_path(tmp_path / "vault", "dev1").is_file()


def test_register_user_private_version_sets_active(tmp_path: Path) -> None:
    register_user_private_version(tmp_path / "vault", "dev1", 1)
    register_user_private_version(tmp_path / "vault", "dev1", 2)
    index = load_user_private_index(tmp_path / "vault", "dev1")
    assert index is not None
    assert index.active_version == 2
    assert set(index.versions) == {"1", "2"}


def test_resolve_prefers_index_active_version(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    device = "dev1"
    v1_pem = vault_user_private_path_for_version(vault, device, 1)
    v2_pem = vault_user_private_path_for_version(vault, device, 2)
    v1_pem.parent.mkdir(parents=True)
    v2_pem.parent.mkdir(parents=True)
    v1_pem.write_bytes(b"v1-pem")
    v2_pem.write_bytes(b"v2-pem")
    register_user_private_version(vault, device, 1)
    register_user_private_version(vault, device, 2)
    assert resolve_user_private_key(vault, device).read_bytes() == b"v2-pem"


def test_resolve_scans_max_version_without_index(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    device = "dev1"
    v1_pem = vault_user_private_path_for_version(vault, device, 1)
    v2_pem = vault_user_private_path_for_version(vault, device, 2)
    v1_pem.parent.mkdir(parents=True)
    v2_pem.parent.mkdir(parents=True)
    v1_pem.write_bytes(b"v1-pem")
    v2_pem.write_bytes(b"v2-pem")
    assert resolve_user_private_key(vault, device).read_bytes() == b"v2-pem"


def test_resolve_legacy_root_fallback(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    device = "dev1"
    legacy = vault_user_private_path(vault, device)
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy-pem")
    assert resolve_user_private_key(vault, device).read_bytes() == b"legacy-pem"
    index_path = user_private_index_path(vault, device)
    assert index_path.is_file()


def test_remove_user_private_version_from_index_reassigns_active(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    device = "dev1"
    register_user_private_version(vault, device, 1)
    register_user_private_version(vault, device, 2)
    remove_user_private_version_from_index(vault, device, 2)
    index = load_user_private_index(vault, device)
    assert index is not None
    assert index.active_version == 1
    assert index.versions == {"1": "rsa/v1/user_private.pem"}


def test_remove_last_version_deletes_index(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    device = "dev1"
    register_user_private_version(vault, device, 1)
    remove_user_private_version_from_index(vault, device, 1)
    assert load_user_private_index(vault, device) is None
    assert not user_private_index_path(vault, device).exists()


def test_resolve_user_private_key_missing(tmp_path: Path) -> None:
    with pytest.raises(CustomerFacingError) as exc:
        resolve_user_private_key(tmp_path / "vault", "missing")
    assert exc.value.message == MSG_DEVICE_PRIVATE_KEY_MISSING


def test_migrate_legacy_binds_to_latest_rsa_version(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    device = "dev1"
    legacy = vault_user_private_path(vault, device)
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy-pem")
    rsa_v2 = legacy.parent / "rsa" / "v2"
    rsa_v2.mkdir(parents=True)
    (rsa_v2 / "public.pem").write_text("pub")
    resolve_user_private_key(vault, device)
    index = json.loads(user_private_index_path(vault, device).read_text(encoding="utf-8"))
    assert index["active_version"] == 2
    assert vault_user_private_path_for_version(vault, device, 2).read_bytes() == b"legacy-pem"
