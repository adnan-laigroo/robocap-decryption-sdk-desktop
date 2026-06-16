from __future__ import annotations

from enum import IntEnum
from typing import Any


class ErrorCode(IntEnum):
    ERR_CUSTOMER_NOT_FOUND = 1001
    ERR_CUSTOMER_ALREADY_EXISTS = 1002
    ERR_KEY_OWNERSHIP_FAILED = 2001
    ERR_CUSTOMER_MISMATCH = 2002
    ERR_RSA_VERSION_MISSING = 3001
    ERR_K2_META_VERSION_MISMATCH = 3002
    ERR_K2_DECODE = 3003
    ERR_K2_PLAINTEXT_LENGTH = 3004
    ERR_SIDECAR_INCOMPLETE = 4001
    ERR_META_VALIDATION = 4002
    ERR_DECRYPT_AUTH_TAG = 5001
    ERR_SHA256_MISMATCH = 5002
    ERR_VAULT_IO = 6001
    ERR_MASTER_KEY = 6002
    ERR_OPENSSL_CLI_UNAVAILABLE = 6003
    ERR_INVALID_RSA_BITS = 6004
    ERR_OPENSSL_CLI_FAILED = 6005
    ERR_RSA_IMPORT_INVALID = 6006
    ERR_RSA_NOT_IMPORTED = 6007
    ERR_DEVICE_AES_EXISTS = 6008
    ERR_RSA_V1_REQUIRED = 6009
    ERR_CENC_TAGS_MISSING = 7001
    ERR_CENC_CEKA_WRAP = 7004
    ERR_CENC_CEKA_LENGTH = 7005
    ERR_FFMPEG_NOT_FOUND = 7006
    ERR_FFPROBE_NOT_FOUND = 7007
    ERR_CENC_DECRYPT_FAILED = 7008
    ERR_CENC_FFPROBE_FAILED = 7009
    ERR_CENC_CUSTOMER_ID_INVALID = 7010
    ERR_CENC_CEKA_TRIAL_FAILED = 7011


class RobocapError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(f"[{code.name}] {message}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": int(self.code),
            "error": self.code.name,
            "message": self.message,
            "detail": self.detail,
        }
