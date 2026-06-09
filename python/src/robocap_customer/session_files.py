from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from robocap_customer.conflict_resolver import ConflictResolver
from robocap_customer.error_mapper import CustomerFacingError, to_db_copy_message


@dataclass
class DbCopyResult:
    total: int
    copied: int
    skipped: int


def scan_plain_db_files(input_root: Path) -> list[Path]:
    """Recursively find plain .db files under input_root (excludes *.db.enc)."""
    root = input_root.expanduser().resolve()
    if not root.is_dir():
        return []

    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        name = path.name.lower()
        if name.endswith(".db.enc"):
            continue
        if name.endswith(".db"):
            found.append(path.resolve())

    return sorted(found)


def copy_plain_db_files(
    db_paths: list[Path],
    *,
    input_root: Path,
    output_root: Path,
    conflict_resolver: ConflictResolver,
) -> DbCopyResult:
    """Copy plain .db files into output_root, preserving relative paths."""
    input_root = input_root.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0

    for db_path in db_paths:
        try:
            relative = db_path.relative_to(input_root)
        except ValueError as exc:
            raise CustomerFacingError(to_db_copy_message(exc)) from exc

        target = output_root / relative
        if target.is_file():
            try:
                rel_target = str(target.relative_to(output_root))
            except ValueError:
                rel_target = target.name
            if conflict_resolver.resolve(rel_target) == "skip":
                skipped += 1
                continue

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(db_path, target)
            copied += 1
        except Exception as exc:
            raise CustomerFacingError(to_db_copy_message(exc)) from exc

    return DbCopyResult(total=len(db_paths), copied=copied, skipped=skipped)
