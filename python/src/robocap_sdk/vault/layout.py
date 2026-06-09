from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

from robocap_sdk.errors import ErrorCode, RobocapError


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        _set_windows_acl(path)
    else:
        path.chmod(stat.S_IRWXU)


def _set_windows_acl(path: Path) -> None:
    try:
        import ctypes

        user = os.environ.get("USERNAME", "")
        if not user:
            return
        cmd = (
            f'icacls "{path}" /inheritance:r /grant:r "{user}:(OI)(CI)F" '
            f'/grant:r "SYSTEM:(OI)(CI)F"'
        )
        os.system(cmd)
    except Exception:
        pass


def atomic_write_bytes(target: Path, data: bytes) -> None:
    ensure_private_dir(target.parent)
    fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".tmp_")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        tmp_path.replace(target)
    except OSError as exc:
        tmp_path.unlink(missing_ok=True)
        raise RobocapError(
            ErrorCode.ERR_VAULT_IO,
            f"Failed to write {target}",
            detail={"path": str(target)},
        ) from exc


def atomic_write_text(target: Path, text: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(target, text.encode(encoding))
