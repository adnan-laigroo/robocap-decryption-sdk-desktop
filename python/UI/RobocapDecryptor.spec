# PyInstaller spec: run from python/UI with `pyinstaller RobocapDecryptor.spec`.
from pathlib import Path
import shutil
import sys

ui_dir = Path(SPECPATH)
python_dir = ui_dir.parent
root_dir = python_dir.parent
script = python_dir / "scripts" / "bulk_decrypt.py"
if not script.is_file():
    raise FileNotFoundError(f"Expected upstream bulk decrypt script: {script}")

# Bundle runtime media tools so end users do not need a separate ffmpeg install.
binary_names = ("ffmpeg.exe", "ffprobe.exe") if sys.platform == "win32" else ("ffmpeg", "ffprobe")
binaries = []
for name in binary_names:
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"{name} must be installed on the build machine and on PATH")
    binaries.append((found, "."))

a = Analysis(
    [str(ui_dir / "main.py")],
    pathex=[str(ui_dir), str(python_dir / "src")],
    binaries=binaries,
    datas=[(str(script), "scripts")],
    hiddenimports=[
        "robocap_decryption_sdk", "robocap_decryption_sdk.cli",
        "cryptography.hazmat.bindings._rust", "PySide6.QtCore",
        "PySide6.QtGui", "PySide6.QtWidgets",
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
if sys.platform == "darwin":
    exe = EXE(
        pyz, a.scripts, [], exclude_binaries=True, name="RobocapDecryptor",
        debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
        console=False, disable_windowed_traceback=False, argv_emulation=False,
        target_arch=None, codesign_identity=None, entitlements_file=None,
    )
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False,
                   name="RobocapDecryptor")
    app = BUNDLE(
        coll, name="RobocapDecryptor.app",
        icon=None, bundle_identifier="org.frodobots.robocapdecryptor",
        info_plist={"CFBundleName": "RobocapDecryptor", "LSMinimumSystemVersion": "11.0"},
    )
else:
    # A single-file executable is convenient for the Windows download.
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [], name="RobocapDecryptor",
        debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
        console=False, disable_windowed_traceback=False, argv_emulation=False,
        target_arch=None, codesign_identity=None, entitlements_file=None,
    )
