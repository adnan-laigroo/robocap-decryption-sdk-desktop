from __future__ import annotations

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from robocap_decryption_sdk.config import (
    AES_KEY_BYTES,
    CEK_BYTES,
    RSA_2048_CIPHERTEXT_BYTES,
    RSA_CIPHERTEXT_BYTES,
)
from robocap_decryption_sdk.errors import ErrorCode, RobocapError

RSA_OAEP_PADDING = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None,
)


def _cipher_len_for_key(key: rsa.RSAPublicKey | rsa.RSAPrivateKey) -> int:
    return key.key_size // 8


def wrap_key(
    plaintext: bytes,
    public_key: rsa.RSAPublicKey,
    *,
    plain_len: int,
    cipher_len: int | None = None,
) -> bytes:
    if len(plaintext) != plain_len:
        raise ValueError(f"plaintext must be {plain_len} bytes")
    expected_cipher_len = cipher_len or _cipher_len_for_key(public_key)
    ciphertext = public_key.encrypt(plaintext, RSA_OAEP_PADDING)
    if len(ciphertext) != expected_cipher_len:
        raise ValueError(
            f"RSA ciphertext length {len(ciphertext)} != {expected_cipher_len}"
        )
    return ciphertext


def unwrap_key(
    ciphertext: bytes,
    private_key: rsa.RSAPrivateKey,
    *,
    plain_len: int,
    cipher_len: int | None = None,
    decode_error: ErrorCode = ErrorCode.ERR_K2_DECODE,
    length_error: ErrorCode = ErrorCode.ERR_K2_PLAINTEXT_LENGTH,
) -> bytes:
    expected_cipher_len = cipher_len or _cipher_len_for_key(private_key)
    if len(ciphertext) != expected_cipher_len:
        raise RobocapError(
            decode_error,
            f"RSA ciphertext must be {expected_cipher_len} bytes",
        )
    try:
        plaintext = private_key.decrypt(ciphertext, RSA_OAEP_PADDING)
    except Exception as exc:
        raise RobocapError(
            decode_error,
            "RSA-OAEP unwrap failed",
        ) from exc
    if len(plaintext) != plain_len:
        raise RobocapError(
            length_error,
            f"Decrypted key length {len(plaintext)} != {plain_len}",
        )
    return plaintext


def wrap_aes_key(device_aes: bytes, public_key: rsa.RSAPublicKey) -> bytes:
    return wrap_key(
        device_aes,
        public_key,
        plain_len=AES_KEY_BYTES,
        cipher_len=RSA_CIPHERTEXT_BYTES,
    )


def unwrap_aes_key(ciphertext: bytes, private_key: rsa.RSAPrivateKey) -> bytes:
    return unwrap_key(
        ciphertext,
        private_key,
        plain_len=AES_KEY_BYTES,
        cipher_len=RSA_CIPHERTEXT_BYTES,
    )


def wrap_cek(cek: bytes, public_key: rsa.RSAPublicKey) -> bytes:
    return wrap_key(
        cek,
        public_key,
        plain_len=CEK_BYTES,
        cipher_len=RSA_2048_CIPHERTEXT_BYTES,
    )


def unwrap_cek(ciphertext: bytes, private_key: rsa.RSAPrivateKey) -> bytes:
    return unwrap_key(
        ciphertext,
        private_key,
        plain_len=CEK_BYTES,
        cipher_len=RSA_2048_CIPHERTEXT_BYTES,
        decode_error=ErrorCode.ERR_CENC_CEKA_WRAP,
        length_error=ErrorCode.ERR_CENC_CEKA_LENGTH,
    )
