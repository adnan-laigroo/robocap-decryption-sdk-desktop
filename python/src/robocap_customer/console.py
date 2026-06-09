from __future__ import annotations

import re

_FORBIDDEN = re.compile(
    r"ERR_|-----BEGIN|\.master_key|(?<![/-])\bRSA\b(?![/-])|\bAES\b|\bK2\b|sidecar|ErrorCode",
    re.IGNORECASE,
)

_SANITIZED_FALLBACK = (
    "Operation could not be completed. Please try again or contact your administrator."
)


def _sanitize(text: str) -> str:
    if _FORBIDDEN.search(text):
        return _SANITIZED_FALLBACK
    return text


def info(msg: str) -> None:
    print(_sanitize(msg))


def error(msg: str) -> None:
    print(_sanitize(msg))


def progress(current: int, total: int, msg: str) -> None:
    print(_sanitize(f"[{current}/{total}] {msg}"))


def summary(
    *,
    succeeded: int,
    failed: int,
    skipped: int,
    db_copied: int | None = None,
) -> None:
    print("")
    print("========== Decryption complete ==========")
    print(f"Succeeded: {succeeded}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    if db_copied is not None:
        print(f"Copied .db files: {db_copied}")


def print_failures(items: list[tuple[str, str]]) -> None:
    if not items:
        return
    print("")
    print("Failed files:")
    for name, message in items:
        print(f"  - {name}: {message}")
