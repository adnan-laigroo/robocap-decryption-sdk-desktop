from __future__ import annotations

from robocap_customer.error_mapper import (
    MSG_BUNDLE_MISSING,
    MSG_CORRUPT,
    MSG_CUSTOMER_NOT_FOUND,
    MSG_DELETE_FAILED,
    MSG_FFMPEG,
    MSG_GEN_CANCELLED,
    MSG_GEN_FAILED,
    MSG_IMPORT_CONFLICT,
    MSG_IMPORT_FAILED,
    MSG_INVALID_CUSTOMER_ID,
    MSG_INVALID_KEY,
    MSG_NO_VERSIONS,
    MSG_DB_COPY_FAILED,
    MSG_OUTPUT_PERM,
    MSG_OWNERSHIP,
    MSG_PREFLIGHT_KEY,
    MSG_VAULT_BAD,
    MSG_VAULT_NOT_WRITABLE,
    CustomerFacingError,
)
from robocap_decryption_sdk.errors import ErrorCode, RobocapError

from robocap_web.api.errors import AppError

_MESSAGE_TO_CODE: dict[str, tuple[str, str]] = {
    MSG_VAULT_NOT_WRITABLE: ("vault_not_writable", "errors.import.vaultNotWritable"),
    MSG_VAULT_BAD: ("vault_invalid", "errors.common.vaultInvalid"),
    MSG_BUNDLE_MISSING: ("bundle_missing", "errors.import.bundleMissing"),
    MSG_INVALID_KEY: ("invalid_key", "errors.import.invalidKey"),
    MSG_INVALID_CUSTOMER_ID: ("invalid_customer_id", "errors.common.invalidCustomerId"),
    MSG_GEN_CANCELLED: ("gen_cancelled", "errors.import.genCancelled"),
    MSG_GEN_FAILED: ("gen_failed", "errors.import.genFailed"),
    MSG_IMPORT_CONFLICT: ("import_conflict", "errors.import.importConflict"),
    MSG_IMPORT_FAILED: ("import_failed", "errors.import.importFailed"),
    MSG_CUSTOMER_NOT_FOUND: ("customer_not_found", "errors.common.customerNotFound"),
    MSG_NO_VERSIONS: ("no_versions", "errors.delete.noVersions"),
    MSG_DELETE_FAILED: ("delete_failed", "errors.delete.deleteFailed"),
    MSG_OWNERSHIP: ("ownership_failed", "errors.decrypt.ownershipFailed"),
    MSG_PREFLIGHT_KEY: ("cenc_mismatch", "errors.decrypt.cencMismatch"),
    MSG_CORRUPT: ("corrupt_file", "errors.decrypt.corruptFile"),
    MSG_FFMPEG: ("ffmpeg_missing", "errors.decrypt.ffmpegMissing"),
    MSG_OUTPUT_PERM: ("output_not_writable", "errors.decrypt.outputNotWritable"),
    MSG_DB_COPY_FAILED: ("db_copy_failed", "errors.decrypt.dbCopyFailed"),
}


def map_exception(exc: BaseException) -> AppError:
    if isinstance(exc, AppError):
        return exc
    if isinstance(exc, CustomerFacingError):
        pair = _MESSAGE_TO_CODE.get(exc.message)
        if pair:
            code, key = pair
            return AppError(code=code, message_key=key)
        return AppError(code="unknown", message_key="errors.common.unknown", status_code=400)
    if isinstance(exc, RobocapError):
        if exc.code == ErrorCode.ERR_VAULT_IO:
            return AppError("vault_not_writable", "errors.import.vaultNotWritable")
        if exc.code == ErrorCode.ERR_CUSTOMER_NOT_FOUND:
            return AppError("customer_not_found", "errors.common.customerNotFound")
        return AppError("unknown", "errors.common.unknown", status_code=400)
    if isinstance(exc, PermissionError):
        return AppError("vault_not_writable", "errors.import.vaultNotWritable")
    return AppError("unknown", "errors.common.unknown", status_code=500)
