from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from robocap_decryption_sdk.config import DEFAULT_SDK_ROOT
from robocap_decryption_sdk.models.key_meta import RsaKeyMeta
from robocap_decryption_sdk.vault.key_vault import KeyVault


@dataclass
class ImportRsaResult:
    customer_id: str
    rsa_key_version: int
    vault_rsa_dir: Path


def import_rsa_key_version(
    customer_id: str,
    public_pem: bytes,
    private_pem: bytes,
    meta: RsaKeyMeta,
    *,
    sdk_root: Path | None = None,
) -> ImportRsaResult:
    root = sdk_root or DEFAULT_SDK_ROOT
    vault = KeyVault(root)
    version = vault.import_rsa_version(
        customer_id, public_pem, private_pem, meta
    )
    return ImportRsaResult(
        customer_id=customer_id,
        rsa_key_version=version,
        vault_rsa_dir=vault.rsa_version_dir(customer_id, version),
    )
