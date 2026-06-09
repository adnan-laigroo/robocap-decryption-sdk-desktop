from __future__ import annotations

from pathlib import Path

from robocap_sdk.config import VAULT_KEYS_DIR
from robocap_sdk.vault.key_vault import KeyVault
from robocap_sdk.vault.layout import ensure_private_dir

from robocap_customer.error_mapper import MSG_VAULT_NOT_WRITABLE, CustomerFacingError


def ensure_vault_layout(vault_root: Path) -> Path:
    root = vault_root.expanduser().resolve()
    keys_root = root / VAULT_KEYS_DIR
    ensure_private_dir(keys_root)
    return root


def next_rsa_version(vault_root: Path, customer_id: str) -> int:
    vault = KeyVault(vault_root.expanduser().resolve())
    versions = vault.list_rsa_versions(customer_id)
    if not versions:
        return 1
    return max(versions) + 1


def assert_vault_writable(vault_root: Path) -> None:
    root = vault_root.expanduser().resolve()
    try:
        ensure_private_dir(root)
        probe = root / ".robocap_vault_write_probe"
        probe.write_bytes(b"x")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        raise CustomerFacingError(MSG_VAULT_NOT_WRITABLE) from exc
