from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SDK_ROOT: Path = Path(
    os.environ.get(
        "robocap_decryption_sdk_ROOT",
        Path.home() / ".robocap-sdk",
    )
)

VAULT_KEYS_DIR = "vault/keys"
VAULT_FILES_DIR = "vault/files"

RSA_BITS = 2048
RSA_BITS_ALLOWED = (2048,)
RSA_PUBLIC_EXPONENT = 65537
RSA_PADDING_SCHEME = "OAEP_SHA256"
RSA_OAEP_HASH = "sha256"
RSA_OAEP_MGF_HASH = "sha256"
RSA_OAEP_LABEL: bytes | None = None
RSA_CIPHERTEXT_BYTES = 512
RSA_2048_CIPHERTEXT_BYTES = 256

CEK_BYTES = 16
AES_KEY_BYTES = 32
AES_NONCE_BYTES = 12
AES_TAG_BYTES = 16

K2_MAGIC = b"RCK2"
K2_FORMAT_VERSION = 1
K2_HEADER_BYTES = 9
K2_BLOB_MIN_BYTES = K2_HEADER_BYTES + RSA_CIPHERTEXT_BYTES
META_FORMAT_VERSION = 1

DEFAULT_AES_BACKEND = "cryptography"
AES_BACKEND_OPENSSL = "openssl_cli"
OPENSSL_ENV_VAR = "ROBOCAP_OPENSSL"
FFMPEG_ENV_VAR = "ROBOCAP_FFMPEG"
FFPROBE_ENV_VAR = "ROBOCAP_FFPROBE"

MASTER_KEY_FILENAME = ".master_key"
DEVICE_AES_FILENAME = "device_aes.enc.pem"

CUSTOMER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class CryptoPolicy:
    rsa_bits: int = RSA_BITS
    rsa_public_exponent: int = RSA_PUBLIC_EXPONENT
    aes_key_bytes: int = AES_KEY_BYTES
    aes_nonce_bytes: int = AES_NONCE_BYTES
    aes_tag_bytes: int = AES_TAG_BYTES
    rsa_ciphertext_bytes: int = RSA_CIPHERTEXT_BYTES


CRYPTO_POLICY = CryptoPolicy()


def validate_customer_id(customer_id: str) -> None:
    if not customer_id or not CUSTOMER_ID_PATTERN.match(customer_id):
        raise ValueError(
            f"Invalid customer_id: {customer_id!r} "
            "(allowed: alphanumeric, underscore, hyphen)"
        )


def keys_vault_root(sdk_root: Path) -> Path:
    return sdk_root / VAULT_KEYS_DIR


def files_vault_root(sdk_root: Path) -> Path:
    return sdk_root / VAULT_FILES_DIR
