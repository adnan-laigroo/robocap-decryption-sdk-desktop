from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Literal

from robocap_decryption_sdk.io.mp4_cenc import CencMp4Metadata
from robocap_decryption_sdk.services.decrypt_cenc import decrypt_cenc_mp4

from robocap_customer import console
from robocap_customer.conflict_resolver import ConflictResolver
from robocap_customer.error_mapper import MSG_OUTPUT_PERM, to_message
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
    session_device_id: str | None = None,
    metadata_by_path: dict[Path, CencMp4Metadata] | None = None,
    max_workers: int = 1,
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

    jobs: list[tuple[int, Path, Path, CencMp4Metadata | None]] = []
    for index, mp4_path in enumerate(mp4_paths, start=1):
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
        try:
            per_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            result.failed += 1
            msg = MSG_OUTPUT_PERM
            result.outcomes.append(
                FileOutcome(mp4_path=mp4_path, status="failed", message=msg)
            )
            _emit_progress(index, len(mp4_paths), msg, progress_fn)
            continue
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

        jobs.append(
            (
                index,
                mp4_path,
                per_dir,
                metadata_by_path.get(mp4_path) if metadata_by_path else None,
            )
        )

    if not jobs:
        return result

    worker_count = max(1, int(max_workers))
    if worker_count == 1:
        for index, mp4_path, per_dir, metadata in jobs:
            if cancel_check is not None and cancel_check():
                break
            _emit_progress(index, len(mp4_paths), "Processing…", progress_fn)
            try:
                decrypt_cenc_mp4(
                    mp4_path,
                    private_pem,
                    per_dir,
                    metadata=metadata,
                    sdk_root=vault_root,
                    session_device_id=session_device_id,
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

    lock = Lock()

    def _decrypt_job(
        job: tuple[int, Path, Path, CencMp4Metadata | None],
    ) -> tuple[int, Path, str | None]:
        index, mp4_path, per_dir, metadata = job
        _emit_progress(index, len(mp4_paths), "Processing…", progress_fn)
        try:
            decrypt_cenc_mp4(
                mp4_path,
                private_pem,
                per_dir,
                metadata=metadata,
                sdk_root=vault_root,
                session_device_id=session_device_id,
            )
            return index, mp4_path, None
        except Exception as exc:  # pragma: no cover - covered via caller assertions
            return index, mp4_path, to_message(exc)

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        in_flight: dict = {}
        next_job = 0
        cancelled = False

        while True:
            while not cancelled and next_job < len(jobs) and len(in_flight) < worker_count:
                if cancel_check is not None and cancel_check():
                    cancelled = True
                    break
                job = jobs[next_job]
                future = executor.submit(_decrypt_job, job)
                in_flight[future] = job
                next_job += 1

            if not in_flight:
                break

            done, _ = wait(in_flight.keys(), return_when=FIRST_COMPLETED)
            for future in done:
                index, mp4_path, message = future.result()
                with lock:
                    if message is None:
                        result.succeeded += 1
                        result.outcomes.append(
                            FileOutcome(mp4_path=mp4_path, status="ok", message=None)
                        )
                        _emit_progress(index, len(mp4_paths), "Done", progress_fn)
                    else:
                        result.failed += 1
                        result.outcomes.append(
                            FileOutcome(
                                mp4_path=mp4_path, status="failed", message=message
                            )
                        )
                        _emit_progress(index, len(mp4_paths), message, progress_fn)
                in_flight.pop(future, None)

    return result
