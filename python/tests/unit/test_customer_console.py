from __future__ import annotations

import re

import pytest

from robocap_customer import console
from robocap_customer.error_mapper import (
    MSG_BUNDLE_MISSING,
    MSG_CENC,
    MSG_CORRUPT,
    MSG_CUSTOMER_NOT_FOUND,
    MSG_DELETE_FAILED,
    MSG_GEN_CANCELLED,
    MSG_GEN_FAILED,
    MSG_FFMPEG,
    MSG_IMPORT_CONFLICT,
    MSG_IMPORT_FAILED,
    MSG_INVALID_CUSTOMER_ID,
    MSG_INVALID_KEY,
    MSG_NO_VERSIONS,
    MSG_OUTPUT_PERM,
    MSG_OWNERSHIP,
    MSG_PREFLIGHT_KEY,
    MSG_SKIP,
    MSG_VAULT_BAD,
    MSG_VAULT_NOT_WRITABLE,
    MSG_VERSION_NOT_FOUND,
)

_FORBIDDEN = re.compile(
    r"ERR_|-----BEGIN|\.master_key|\bRSA\b|\bAES\b|\bK2\b|sidecar|ErrorCode",
    re.IGNORECASE,
)

_ALL_CUSTOMER_MESSAGES = [
    MSG_VAULT_BAD,
    MSG_VAULT_NOT_WRITABLE,
    MSG_BUNDLE_MISSING,
    MSG_INVALID_KEY,
    MSG_INVALID_CUSTOMER_ID,
    MSG_IMPORT_CONFLICT,
    MSG_IMPORT_FAILED,
    MSG_CUSTOMER_NOT_FOUND,
    MSG_NO_VERSIONS,
    MSG_VERSION_NOT_FOUND,
    MSG_DELETE_FAILED,
    MSG_OWNERSHIP,
    MSG_CORRUPT,
    MSG_OUTPUT_PERM,
    MSG_SKIP,
    MSG_FFMPEG,
    MSG_CENC,
    MSG_PREFLIGHT_KEY,
    console._SANITIZED_FALLBACK,
]


@pytest.mark.parametrize("message", _ALL_CUSTOMER_MESSAGES)
def test_customer_messages_pass_console_sanitize(message: str) -> None:
    assert _FORBIDDEN.search(message) is None
    assert console._sanitize(message) == message


def test_vault_path_with_rsa_segment_not_sanitized() -> None:
    path_msg = "Keys stored at: /home/z/vault/vault/keys/openai-1/rsa/v2"
    assert console._sanitize(path_msg) == path_msg
