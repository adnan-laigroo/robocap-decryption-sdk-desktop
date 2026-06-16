from __future__ import annotations

from pathlib import Path

from robocap_decryption_sdk.io.mp4_cenc import has_cenc_tags


def scan_cenc_mp4(input_root: Path) -> list[Path]:
    """Recursively find CENC-tagged MP4 files under input_root."""
    root = input_root.expanduser().resolve()
    if not root.is_dir():
        return []

    found: list[Path] = []
    for path in root.rglob("*.mp4"):
        if not path.is_file():
            continue
        if path.name.endswith(".enc"):
            continue
        resolved = path.resolve()
        if has_cenc_tags(resolved):
            found.append(resolved)

    return sorted(found)
