from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from robocap_decryption_sdk.config import DEFAULT_SDK_ROOT
from robocap_decryption_sdk.errors import ErrorCode, RobocapError
from robocap_decryption_sdk.vault.key_vault import KeyVault


@dataclass
class VerifiedKeyVersion:
    customer_id: str
    matched_rsa_key_version: int
    public_fingerprint: str


def spki_fingerprint(public_key: rsa.RSAPublicKey) -> str:
    der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(der).hexdigest()


def verify_customer_private_key(
    customer_id: str,
    user_private_pem: bytes,
    *,
    key_vault: KeyVault | None = None,
    sdk_root: Path | None = None,
) -> VerifiedKeyVersion:
    root = sdk_root or DEFAULT_SDK_ROOT
    vault = key_vault or KeyVault(root)

    if not vault.exists_customer(customer_id):
        raise RobocapError(
            ErrorCode.ERR_CUSTOMER_NOT_FOUND,
            f"Customer {customer_id} not found in key vault",
        )

    try:
        private_key = serialization.load_pem_private_key(
            user_private_pem, password=None
        )
    except Exception as exc:
        raise RobocapError(
            ErrorCode.ERR_KEY_OWNERSHIP_FAILED,
            "Failed to parse user private key",
        ) from exc

    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise RobocapError(
            ErrorCode.ERR_KEY_OWNERSHIP_FAILED,
            "User key is not an RSA private key",
        )

    user_public = private_key.public_key()
    user_fp = spki_fingerprint(user_public)

    for version in vault.list_rsa_versions(customer_id):
        archived_public = vault.get_public_key(customer_id, version)
        archived_fp = spki_fingerprint(archived_public)
        if user_fp == archived_fp:
            return VerifiedKeyVersion(
                customer_id=customer_id,
                matched_rsa_key_version=version,
                public_fingerprint=user_fp,
            )

    raise RobocapError(
        ErrorCode.ERR_KEY_OWNERSHIP_FAILED,
        f"User private key does not match any archived key for {customer_id}",
    )
