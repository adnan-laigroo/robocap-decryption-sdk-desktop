from __future__ import annotations

from robocap_decryption_sdk.errors import ErrorCode, RobocapError

MSG_VAULT_BAD = "Key vault not found or invalid."
MSG_VAULT_NOT_WRITABLE = "Key vault directory is not writable."
MSG_BUNDLE_MISSING = (
    "Key bundle is missing required files "
    "(rsa_public_spki.pem and rsa_private_pkcs8.pem)."
)
MSG_INVALID_KEY = "Key files are invalid or not 2048-bit keys."
MSG_INVALID_CUSTOMER_ID = (
    "Customer ID is invalid. Use letters, numbers, underscore, or hyphen only."
)
MSG_IMPORT_CONFLICT = (
    "This key version already exists in the vault. Contact support."
)
MSG_IMPORT_FAILED = "Keys could not be imported into the vault."
MSG_GEN_CANCELLED = "Key generation cancelled."
MSG_GEN_FAILED = "Keys could not be generated."
MSG_CUSTOMER_NOT_FOUND = "Customer not found in key vault."
MSG_NO_VERSIONS = "No key versions found for this customer."
MSG_VERSION_NOT_FOUND = "Key version not found in vault."
MSG_DELETE_FAILED = "Key version could not be deleted."
MSG_OWNERSHIP = "Private key ownership check failed."
MSG_CORRUPT = "Encrypted file is corrupted or cannot be decrypted."
MSG_OUTPUT_PERM = "Output directory is not writable."
MSG_SKIP = "This file could not be decrypted and was skipped."
MSG_FFMPEG = "FFmpeg/ffprobe not found. Cannot decrypt CENC video."
MSG_CENC = "Video is missing CENC metadata or the key vault does not match."
MSG_PREFLIGHT_KEY = (
    "Key vault does not match this video. "
    "Confirm the device public key matches the keys imported into the vault."
)
MSG_DB_COPY_FAILED = "Session files could not be copied to the output directory."

_OWNERSHIP_CODES = frozenset(
    {
        ErrorCode.ERR_CUSTOMER_NOT_FOUND,
        ErrorCode.ERR_KEY_OWNERSHIP_FAILED,
        ErrorCode.ERR_CUSTOMER_MISMATCH,
    }
)

_CORRUPT_CODES = frozenset(
    {
        ErrorCode.ERR_CENC_TAGS_MISSING,
        ErrorCode.ERR_CENC_CEKA_WRAP,
        ErrorCode.ERR_CENC_CEKA_LENGTH,
        ErrorCode.ERR_CENC_CUSTOMER_ID_INVALID,
        ErrorCode.ERR_CENC_DECRYPT_FAILED,
        ErrorCode.ERR_CENC_FFPROBE_FAILED,
    }
)

_FFMPEG_CODES = frozenset(
    {
        ErrorCode.ERR_FFMPEG_NOT_FOUND,
        ErrorCode.ERR_FFPROBE_NOT_FOUND,
    }
)

_CENC_KEY_CODES = frozenset(
    {
        ErrorCode.ERR_CENC_CEKA_TRIAL_FAILED,
    }
)


class CustomerFacingError(Exception):
    """Startup-level error with a customer-safe English message."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


_IMPORT_KEY_CODES = frozenset(
    {
        ErrorCode.ERR_INVALID_RSA_BITS,
        ErrorCode.ERR_RSA_IMPORT_INVALID,
    }
)


def to_delete_message(exc: BaseException) -> str:
    if isinstance(exc, CustomerFacingError):
        return exc.message
    if isinstance(exc, RobocapError):
        if exc.code == ErrorCode.ERR_CUSTOMER_NOT_FOUND:
            return MSG_CUSTOMER_NOT_FOUND
        if exc.code == ErrorCode.ERR_RSA_VERSION_MISSING:
            return MSG_VERSION_NOT_FOUND
        if exc.code == ErrorCode.ERR_VAULT_IO:
            return MSG_VAULT_NOT_WRITABLE
        return MSG_DELETE_FAILED
    if isinstance(exc, PermissionError):
        return MSG_VAULT_NOT_WRITABLE
    if isinstance(exc, OSError) and getattr(exc, "errno", None) in (13, 30):
        return MSG_VAULT_NOT_WRITABLE
    return MSG_DELETE_FAILED


def to_import_message(exc: BaseException) -> str:
    if isinstance(exc, CustomerFacingError):
        return exc.message
    if isinstance(exc, RobocapError):
        if exc.code == ErrorCode.ERR_CUSTOMER_ALREADY_EXISTS:
            return MSG_IMPORT_CONFLICT
        if exc.code in _IMPORT_KEY_CODES:
            return MSG_INVALID_KEY
        if exc.code == ErrorCode.ERR_VAULT_IO:
            return MSG_VAULT_NOT_WRITABLE
        return MSG_IMPORT_FAILED
    if isinstance(exc, PermissionError):
        return MSG_VAULT_NOT_WRITABLE
    if isinstance(exc, OSError) and getattr(exc, "errno", None) in (13, 30):
        return MSG_VAULT_NOT_WRITABLE
    return MSG_IMPORT_FAILED


def to_db_copy_message(exc: BaseException) -> str:
    if isinstance(exc, CustomerFacingError):
        return exc.message
    if isinstance(exc, PermissionError):
        return MSG_OUTPUT_PERM
    if isinstance(exc, OSError) and getattr(exc, "errno", None) in (13, 30):
        return MSG_OUTPUT_PERM
    return MSG_DB_COPY_FAILED


def to_message(exc: BaseException) -> str:
    if isinstance(exc, RobocapError):
        if exc.code in _OWNERSHIP_CODES:
            return MSG_OWNERSHIP
        if exc.code in _CORRUPT_CODES:
            return MSG_CORRUPT
        if exc.code in _FFMPEG_CODES:
            return MSG_FFMPEG
        if exc.code in _CENC_KEY_CODES:
            return MSG_CENC
        if exc.code == ErrorCode.ERR_VAULT_IO:
            return MSG_OUTPUT_PERM
        return MSG_SKIP
    if isinstance(exc, PermissionError):
        return MSG_OUTPUT_PERM
    if isinstance(exc, OSError) and getattr(exc, "errno", None) in (13, 30):
        return MSG_OUTPUT_PERM
    return MSG_SKIP
