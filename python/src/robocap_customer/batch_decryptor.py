from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from robocap_sdk.services.decrypt_cenc import decrypt_cenc_mp4

from robocap_customer import console
from robocap_customer.conflict_resolver import ConflictResolver
from robocap_customer.error_mapper import to_message
from robocap_customer.output_renamer import target_cenc_path


@dataclass
class FileOutcome:
    mp4_path: Path
    status: Literal["ok", "skipped", "failed"]
    message: str | None = None


@dataclass
class BatchResult:
    total: int
    succeeded: int
    failed: int
    skipped: int
    outcomes: list[FileOutcome] = field(default_factory=list)


def _emit_progress(
    index: int,
    total: int,
    message: str,
    progress_fn: Callable[[int, int, str], None] | None,
) -> None:
    if progress_fn is not None:
        progress_fn(index, total, message)
    else:
        console.progress(index, total, message)


def run_batch(
    mp4_paths: list[Path],
    *,
    vault_root: Path,
    private_pem: bytes,
    input_root: Path,
    output_root: Path,
    conflict_resolver: ConflictResolver,
    progress_fn: Callable[[int, int, str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> BatchResult:
    input_root = input_root.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    vault_root = vault_root.expanduser().resolve()

    result = BatchResult(
        total=len(mp4_paths),
        succeeded=0,
        failed=0,
        skipped=0,
    )

    for index, mp4_path in enumerate(mp4_paths, start=1):
        if cancel_check is not None and cancel_check():
            break
        _emit_progress(index, len(mp4_paths), "Processing…", progress_fn)

        try:
            relative_parent = mp4_path.parent.relative_to(input_root)
        except ValueError:
            result.failed += 1
            msg = to_message(ValueError("path outside input root"))
            result.outcomes.append(
                FileOutcome(mp4_path=mp4_path, status="failed", message=msg)
            )
            _emit_progress(index, len(mp4_paths), msg, progress_fn)
            continue

        per_dir = output_root / relative_parent
        per_dir.mkdir(parents=True, exist_ok=True)
        target = target_cenc_path(mp4_path, per_dir)

        if target.is_file():
            try:
                rel_target = str(target.relative_to(output_root))
            except ValueError:
                rel_target = target.name
            decision = conflict_resolver.resolve(rel_target)
            if decision == "skip":
                result.skipped += 1
                skip_msg = "Target file already exists; skipped."
                result.outcomes.append(
                    FileOutcome(mp4_path=mp4_path, status="skipped", message=skip_msg)
                )
                _emit_progress(index, len(mp4_paths), skip_msg, progress_fn)
                continue

        try:
            decrypt_cenc_mp4(
                mp4_path,
                private_pem,
                per_dir,
                sdk_root=vault_root,
            )
            result.succeeded += 1
            result.outcomes.append(
                FileOutcome(mp4_path=mp4_path, status="ok", message=None)
            )
            _emit_progress(index, len(mp4_paths), "Done", progress_fn)
        except Exception as exc:
            result.failed += 1
            msg = to_message(exc)
            result.outcomes.append(
                FileOutcome(mp4_path=mp4_path, status="failed", message=msg)
            )
            _emit_progress(index, len(mp4_paths), msg, progress_fn)

    return result
