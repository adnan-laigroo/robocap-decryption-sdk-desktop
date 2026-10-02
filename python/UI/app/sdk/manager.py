from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import queue
import runpy
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, Iterator

from robocap_decryption_sdk.config import DEFAULT_SDK_ROOT


def resource_path(relative: str) -> Path:
    """Resolve bundled resources or the source checkout, independent of cwd."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
    return base / relative


class _LineWriter(io.TextIOBase):
    def __init__(self, emit: Callable[[str], None]):
        self.emit = emit
        self.pending = ""
        self.lock = threading.Lock()

    def write(self, value: str) -> int:
        with self.lock:
            self.pending += value
            while "\n" in self.pending:
                line, self.pending = self.pending.split("\n", 1)
                if line:
                    self.emit(line.rstrip("\r"))
        return len(value)

    def flush(self) -> None:
        with self.lock:
            if self.pending:
                self.emit(self.pending.rstrip("\r"))
                self.pending = ""


class SDKManager:
    def __init__(self):
        self.sdk_cmd = shutil.which("robocap-decryption-sdk")
        self.sdk_root = DEFAULT_SDK_ROOT
        self.bulk_script = self._find_bulk_script()
        if getattr(sys, "frozen", False):
            ffmpeg = resource_path("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
            ffprobe = resource_path("ffprobe.exe" if sys.platform == "win32" else "ffprobe")
            if ffmpeg.is_file():
                os.environ["ROBOCAP_FFMPEG"] = str(ffmpeg)
            if ffprobe.is_file():
                os.environ["ROBOCAP_FFPROBE"] = str(ffprobe)

    @staticmethod
    def _find_bulk_script() -> Path | None:
        # A frozen build ships only the canonical upstream script at scripts/.
        candidates = [resource_path("scripts/bulk_decrypt.py")]
        # UI lives in python/UI; source execution must select python/scripts,
        # never UI/scripts (which is a historical duplicate copy).
        source_python = Path(__file__).resolve().parents[3]
        candidates.append(source_python / "scripts" / "bulk_decrypt.py")
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
        return None

    def sdk_exists(self) -> bool:
        # The SDK package is bundled with the GUI; this indicates CLI presence
        # only for diagnostic purposes.
        return importlib.util.find_spec("robocap_decryption_sdk") is not None

    def vault_exists(self) -> bool:
        return (self.sdk_root / "vault" / "keys").is_dir()

    def bulk_script_exists(self) -> bool:
        return self.bulk_script is not None

    def version(self) -> str:
        return "Bundled SDK" if self.sdk_exists() else "SDK package missing"

    def list_devices(self):
        devices = []
        root = self.sdk_root / "vault" / "keys"
        if not root.exists():
            return devices
        for device in sorted(root.iterdir()):
            rsa = device / "rsa"
            if rsa.is_dir():
                versions = [p.name for p in sorted(rsa.iterdir()) if p.is_dir()]
                if versions:
                    devices.append({"device": device.name, "versions": versions})
        return devices

    def import_key(self, customer_id, version, public_key, private_key):
        # Keep private PEM bytes in memory only; the SDK writes the protected
        # vault copy and validates that public/private files match.
        from datetime import datetime, timezone
        from robocap_decryption_sdk.models.key_meta import RsaKeyMeta
        from robocap_decryption_sdk.services.rsa_import import import_rsa_key_version
        from robocap_decryption_sdk.errors import RobocapError

        try:
            result = import_rsa_key_version(
                customer_id,
                Path(public_key).read_bytes(),
                Path(private_key).read_bytes(),
                RsaKeyMeta(
                    rsa_key_version=int(version),
                    effective_at=datetime.now(timezone.utc),
                    device_id=customer_id,
                ),
                sdk_root=self.sdk_root,
            )
            return 0, f"Imported {result.customer_id} v{result.rsa_key_version}", ""
        except RobocapError as exc:
            message = f"{exc.code.name}: {exc.message}"
            if exc.code.name == "ERR_CUSTOMER_ALREADY_EXISTS":
                message = f"ERR_CUSTOMER_ALREADY_EXISTS: {exc.message}"
            return 1, "", message
        except Exception as exc:
            # A malformed PEM or invalid device name should not prevent the
            # importer from continuing with other matched key pairs.
            return 1, "", f"{type(exc).__name__}: {exc}"

    def bulk_decrypt(
        self, input_path, output_path, workers=8,
        on_line: Callable[[str], None] | None = None,
    ) -> Iterator[str]:
        if self.bulk_script is None:
            raise FileNotFoundError("Could not locate upstream scripts/bulk_decrypt.py")
        input_path = Path(input_path).expanduser().resolve()
        output_path = Path(output_path).expanduser().resolve()
        args = ["--root", str(input_path), "--output-dir", str(output_path),
                "--workers", str(workers), "--sdk-root", str(self.sdk_root),
                "--done-file", str(output_path / ".robocap-decrypt-done.txt")]

        if not getattr(sys, "frozen", False):
            cmd = [sys.executable, "-u", str(self.bulk_script), *args]
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            assert process.stdout is not None
            for line in process.stdout:
                yield line.rstrip()
            code = process.wait()
        else:
            # The upstream script is bundled as data and run with the SDK in
            # the frozen interpreter; sys.executable is never used as Python.
            lines: queue.Queue[str | None] = queue.Queue()
            outcome: list[int] = []

            def execute():
                old_argv = sys.argv
                writer = _LineWriter(lines.put)
                try:
                    sys.argv = [str(self.bulk_script), *args]
                    with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                        try:
                            runpy.run_path(str(self.bulk_script), run_name="__main__")
                        except SystemExit as exc:
                            outcome.append(int(exc.code or 0))
                    writer.flush()
                    if not outcome:
                        outcome.append(0)
                except BaseException as exc:
                    lines.put(f"Bulk decrypt failed: {exc}")
                    outcome.append(1)
                finally:
                    sys.argv = old_argv
                    lines.put(None)

            thread = threading.Thread(target=execute, name="RobocapBulkDecrypt", daemon=True)
            thread.start()
            while True:
                line = lines.get()
                if line is None:
                    break
                yield line
            thread.join()
            code = outcome[0] if outcome else 1

        if code:
            yield f"Process exited with code {code}"
