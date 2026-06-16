from __future__ import annotations

import base64
import os

import pytest
from cryptography.hazmat.primitives import serialization

from robocap_decryption_sdk.config import CEK_BYTES, RSA_2048_CIPHERTEXT_BYTES
from robocap_decryption_sdk.crypto.rsa_oaep import unwrap_cek, unwrap_key, wrap_cek, wrap_key
from robocap_decryption_sdk.errors import ErrorCode, RobocapError
from robocap_decryption_sdk.io.mp4_cenc import parse_cenc_metadata_from_tags
from tests.helpers import generate_rsa_keypair


def test_rsa_wrap_unwrap_roundtrip_2048():
    public_pem, private_pem = generate_rsa_keypair(bits=2048)
    public_key = serialization.load_pem_public_key(public_pem)
    private_key = serialization.load_pem_private_key(private_pem, password=None)
    payload = os.urandom(CEK_BYTES)
    wrapped = wrap_key(
        payload,
        public_key,
        plain_len=CEK_BYTES,
        cipher_len=RSA_2048_CIPHERTEXT_BYTES,
    )
    unwrapped = unwrap_key(
        wrapped,
        private_key,
        plain_len=CEK_BYTES,
        cipher_len=RSA_2048_CIPHERTEXT_BYTES,
    )
    assert unwrapped == payload


def test_rsa_wrap_unwrap_roundtrip_4096():
    public_pem, private_pem = generate_rsa_keypair(bits=4096)
    public_key = serialization.load_pem_public_key(public_pem)
    private_key = serialization.load_pem_private_key(private_pem, password=None)
    payload = os.urandom(32)
    wrapped = wrap_key(payload, public_key, plain_len=32, cipher_len=512)
    unwrapped = unwrap_key(wrapped, private_key, plain_len=32, cipher_len=512)
    assert unwrapped == payload


def test_wrap_unwrap_cek():
    public_pem, private_pem = generate_rsa_keypair(bits=2048)
    public_key = serialization.load_pem_public_key(public_pem)
    private_key = serialization.load_pem_private_key(private_pem, password=None)
    cek = os.urandom(CEK_BYTES)
    wrapped = wrap_cek(cek, public_key)
    assert len(wrapped) == RSA_2048_CIPHERTEXT_BYTES
    assert unwrap_cek(wrapped, private_key) == cek


def test_parse_cenc_metadata_from_tags():
    public_pem, private_pem = generate_rsa_keypair(bits=2048)
    public_key = serialization.load_pem_public_key(public_pem)
    cek = os.urandom(CEK_BYTES)
    wrapped = wrap_cek(cek, public_key)
    tags = {
        "cenc_customer_id": "CENC_CUST",
        "cenc_cek_wrapped_b64": base64.b64encode(wrapped).decode("ascii"),
        "cenc_kid_hex": "ab" * 16,
    }
    meta = parse_cenc_metadata_from_tags(tags)
    assert meta.customer_id == "CENC_CUST"
    assert meta.cek_wrapped == wrapped


def test_parse_cenc_metadata_missing_tags():
    with pytest.raises(RobocapError) as exc:
        parse_cenc_metadata_from_tags({"cenc_cek_wrapped_b64": "AA=="})
    assert exc.value.code == ErrorCode.ERR_CENC_TAGS_MISSING


def test_parse_cenc_metadata_invalid_customer_id():
    with pytest.raises(RobocapError) as exc:
        parse_cenc_metadata_from_tags(
            {
                "cenc_customer_id": "bad id",
                "cenc_cek_wrapped_b64": "AA==",
            }
        )
    assert exc.value.code == ErrorCode.ERR_CENC_CUSTOMER_ID_INVALID
