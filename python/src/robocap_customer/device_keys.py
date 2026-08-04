from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from robocap_decryption_sdk.config import keys_vault_root, validate_customer_id
from robocap_decryption_sdk.vault.layout import atomic_write_text

from robocap_customer.error_mapper import (
    MSG_DEVICE_PRIVATE_KEY_MISSING,
    MSG_INVALID_CUSTOMER_ID,
    CustomerFacingError,
)
from robocap_customer.key_bundle import USER_PRIVATE_PEM_NAME

USER_PRIVATE_INDEX_NAME = "user_private_index.json"
_RSA_VERSION_DIR = re.compile(r"^v(\d+)$")


@dataclass
class UserPrivateIndex:
    device_id: str
    active_version: int
    versions: dict[str, str] = field(default_factory=dict)
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "active_version": self.active_version,
            "versions": dict(sorted(self.versions.items(), key=lambda kv: int(kv[0]))),
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> UserPrivateIndex:
        versions_raw = data.get("versions") or {}
        versions = {str(k): str(v) for k, v in versions_raw.items()}
        return cls(
            device_id=str(data.get("device_id", "")),
            active_version=int(data.get("active_version", 0)),
            versions=versions,
            updated_at=str(data.get("updated_at", "")),
        )


def _device_dir(vault_root: Path, device_id: str) -> Path:
    root = vault_root.expanduser().resolve()
    validate_customer_id(device_id.strip())
    return keys_vault_root(root) / device_id.strip()


def vault_user_private_path(vault_root: Path, device_id: str) -> Path:
    return _device_dir(vault_root, device_id) / USER_PRIVATE_PEM_NAME


def vault_user_private_path_for_version(
    vault_root: Path,
    device_id: str,
    version: int,
) -> Path:
    return _device_dir(vault_root, device_id) / "rsa" / f"v{version}" / USER_PRIVATE_PEM_NAME


def user_private_index_path(vault_root: Path, device_id: str) -> Path:
    return _device_dir(vault_root, device_id) / USER_PRIVATE_INDEX_NAME


def _relative_user_private_path(version: int) -> str:
    return f"rsa/v{version}/{USER_PRIVATE_PEM_NAME}"


def load_user_private_index(vault_root: Path, device_id: str) -> UserPrivateIndex | None:
    path = user_private_index_path(vault_root, device_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return UserPrivateIndex.from_dict(data)


def save_user_private_index(
    vault_root: Path,
    index: UserPrivateIndex,
) -> None:
    index.updated_at = datetime.now(timezone.utc).isoformat()
    path = user_private_index_path(vault_root, index.device_id)
    atomic_write_text(path, json.dumps(index.to_dict(), indent=2) + "\n")


def register_user_private_version(
    vault_root: Path,
    device_id: str,
    version: int,
) -> UserPrivateIndex:
    normalized = device_id.strip()
    rel = _relative_user_private_path(version)
    index = load_user_private_index(vault_root, normalized)
    if index is None:
        index = UserPrivateIndex(device_id=normalized, active_version=version)
    index.device_id = normalized
    index.versions[str(version)] = rel
    index.active_version = version
    save_user_private_index(vault_root, index)
    return index


def scan_rsa_user_private_versions(vault_root: Path, device_id: str) -> dict[int, Path]:
    rsa_dir = _device_dir(vault_root, device_id) / "rsa"
    found: dict[int, Path] = {}
    if not rsa_dir.is_dir():
        return found
    for child in rsa_dir.iterdir():
        if not child.is_dir():
            continue
        match = _RSA_VERSION_DIR.match(child.name)
        if not match:
            continue
        pem = child / USER_PRIVATE_PEM_NAME
        if pem.is_file():
            found[int(match.group(1))] = pem.resolve()
    return found


def list_rsa_key_versions(vault_root: Path, device_id: str) -> list[int]:
    rsa_dir = _device_dir(vault_root, device_id) / "rsa"
    versions: list[int] = []
    if not rsa_dir.is_dir():
        return versions
    for child in rsa_dir.iterdir():
        if not child.is_dir():
            continue
        match = _RSA_VERSION_DIR.match(child.name)
        if match:
            versions.append(int(match.group(1)))
    return sorted(versions)


def remove_user_private_version_from_index(
    vault_root: Path,
    device_id: str,
    version: int,
) -> None:
    index = load_user_private_index(vault_root, device_id)
    if index is None:
        return
    index.versions.pop(str(version), None)
    if not index.versions:
        user_private_index_path(vault_root, device_id).unlink(missing_ok=True)
        return
    if index.active_version == version:
        remaining = sorted(int(v) for v in index.versions)
        index.active_version = remaining[-1]
    save_user_private_index(vault_root, index)


def _resolve_from_index(vault_root: Path, device_id: str) -> Path | None:
    index = load_user_private_index(vault_root, device_id)
    if index is None or not index.versions:
        return None
    active = index.active_version
    rel = index.versions.get(str(active))
    if rel is None:
        latest = max(int(v) for v in index.versions)
        rel = index.versions[str(latest)]
    path = (_device_dir(vault_root, device_id) / rel).resolve()
    return path if path.is_file() else None


def _resolve_from_scan(vault_root: Path, device_id: str) -> Path | None:
    scanned = scan_rsa_user_private_versions(vault_root, device_id)
    if not scanned:
        return None
    return scanned[max(scanned)]


def migrate_legacy_user_private_if_needed(vault_root: Path, device_id: str) -> None:
    if load_user_private_index(vault_root, device_id) is not None:
        return
    legacy = vault_user_private_path(vault_root, device_id)
    if not legacy.is_file():
        return
    legacy_bytes = legacy.read_bytes()
    scanned = scan_rsa_user_private_versions(vault_root, device_id)
    if scanned:
        matched = next(
            (v for v, path in scanned.items() if path.read_bytes() == legacy_bytes),
            None,
        )
        if matched is not None:
            version = matched
        else:
            version = max(scanned)
            target = vault_user_private_path_for_version(vault_root, device_id, version)
            if not target.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(legacy_bytes)
    else:
        rsa_versions = list_rsa_key_versions(vault_root, device_id)
        version = rsa_versions[-1] if rsa_versions else 1
        target = vault_user_private_path_for_version(vault_root, device_id, version)
        if not target.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(legacy_bytes)
    register_user_private_version(vault_root, device_id, version)


def resolve_user_private_key(vault_root: Path, device_id: str) -> Path:
    normalized = device_id.strip()
    if not normalized:
        raise CustomerFacingError(MSG_INVALID_CUSTOMER_ID)
    try:
        validate_customer_id(normalized)
    except ValueError as exc:
        raise CustomerFacingError(MSG_INVALID_CUSTOMER_ID) from exc

    migrate_legacy_user_private_if_needed(vault_root, normalized)

    for resolver in (_resolve_from_index, _resolve_from_scan):
        path = resolver(vault_root, normalized)
        if path is not None:
            return path

    legacy = vault_user_private_path(vault_root, normalized)
    if legacy.is_file():
        return legacy

    raise CustomerFacingError(MSG_DEVICE_PRIVATE_KEY_MISSING)
