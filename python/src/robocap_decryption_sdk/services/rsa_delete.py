from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from robocap_decryption_sdk.config import DEFAULT_SDK_ROOT
from robocap_decryption_sdk.vault.key_vault import KeyVault


@dataclass
class DeleteRsaResult:
    customer_id: str
    folder_name: str
    key_dir: Path


def delete_rsa_key_version(
    customer_id: str,
    rsa_key_version: int,
    *,
    sdk_root: Path | None = None,
) -> DeleteRsaResult:
    root = sdk_root or DEFAULT_SDK_ROOT
    vault = KeyVault(root)
    key_dir = vault.rsa_version_dir(customer_id, rsa_key_version)
    vault.delete_rsa_version(customer_id, rsa_key_version)
    return DeleteRsaResult(
        customer_id=customer_id,
        folder_name=key_dir.name,
        key_dir=key_dir,
    )


def delete_rsa_key_dir(
    customer_id: str,
    key_dir: Path,
    *,
    sdk_root: Path | None = None,
) -> DeleteRsaResult:
    root = sdk_root or DEFAULT_SDK_ROOT
    vault = KeyVault(root)
    resolved = key_dir.expanduser().resolve()
    folder_name = resolved.name
    vault.delete_rsa_key_dir(customer_id, resolved)
    return DeleteRsaResult(
        customer_id=customer_id,
        folder_name=folder_name,
        key_dir=resolved,
    )
