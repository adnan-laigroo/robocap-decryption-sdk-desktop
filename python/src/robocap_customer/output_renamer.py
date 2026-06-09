from __future__ import annotations

from pathlib import Path


def target_cenc_path(mp4_path: Path, per_dir: Path) -> Path:
    return per_dir / mp4_path.name
