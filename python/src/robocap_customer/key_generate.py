from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from robocap_customer.key_bundle import (
    PRIVATE_PEM_NAME,
    PUBLIC_PEM_NAME,
    USER_PRIVATE_PEM_NAME,
)


def generate_cenc_key_bundle(output_dir: Path, *, include_user_private: bool = True) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    (output_dir / PUBLIC_PEM_NAME).write_bytes(pub_pem)
    (output_dir / PRIVATE_PEM_NAME).write_bytes(priv_pem)

    if include_user_private:
        (output_dir / USER_PRIVATE_PEM_NAME).write_bytes(priv_pem)

    return output_dir.resolve()
