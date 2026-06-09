from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from collections.abc import Callable

from robocap_customer import console
from robocap_customer.batch_decryptor import BatchResult, run_batch
from robocap_customer.bootstrap import init_customer_logging
from robocap_customer.config import CustomerConfig
from robocap_customer.conflict_resolver import ConflictMode, ConflictResolver
from robocap_customer.error_mapper import CustomerFacingError
from robocap_customer.preflight import preflight_cenc_mp4
from robocap_customer.scanner import scan_cenc_mp4
from robocap_customer.session_files import copy_plain_db_files, scan_plain_db_files
from robocap_customer.vault_validator import (
    load_user_private_pem,
    validate_output_writable,
    validate_vault_structure,
)


@dataclass
class SessionInput:
    vault_root: Path
    user_private_key_path: Path
    input_root: Path
    output_root: Path


def _prompt_path(
    label: str,
    default: str | None = None,
    *,
    must_be_dir: bool = True,
) -> Path:
    while True:
        if default:
            raw = input(f"{label} [{default}]: ").strip()
            value = raw or default
        else:
            value = input(f"{label}: ").strip()
        if not value:
            console.error("Path cannot be empty. Please try again.")
            continue
        path = Path(value).expanduser()
        if must_be_dir and not path.is_dir():
            console.error("Directory does not exist. Please try again.")
            continue
        return path.resolve()


def _prompt_file_path(label: str, default: str | None = None) -> Path:
    while True:
        if default:
            raw = input(f"{label} [{default}]: ").strip()
            value = raw or default
        else:
            value = input(f"{label}: ").strip()
        if not value:
            console.error("Path cannot be empty. Please try again.")
            continue
        path = Path(value).expanduser()
        if not path.is_file():
            console.error("File does not exist. Please try again.")
            continue
        return path.resolve()


def collect_session_input() -> SessionInput:
    vault_root = _prompt_path("Vault path", must_be_dir=True)
    loaded = CustomerConfig.load(vault_root)
    user_key_default = (
        str(loaded.user_private_key_path)
        if loaded and loaded.user_private_key_path
        else None
    )
    user_private_key_path = _prompt_file_path(
        "User private key PEM path",
        default=user_key_default,
    )
    input_root = _prompt_path("Encrypted input directory", must_be_dir=True)
    output_root = _prompt_path("Decrypted output directory", must_be_dir=False)
    return SessionInput(
        vault_root=vault_root,
        user_private_key_path=user_private_key_path,
        input_root=input_root,
        output_root=output_root.resolve(),
    )


class InteractiveConflictResolver:
    def __init__(self) -> None:
        self._mode = ConflictMode.ASK

    def resolve(self, relative_target: str) -> str:
        if self._mode == ConflictMode.SKIP_ALL:
            return "skip"
        if self._mode == ConflictMode.OVERWRITE_ALL:
            return "overwrite"

        console.info(f"Target already exists: {relative_target}")
        console.info("Choose an option:")
        console.info("  1 - Skip this file")
        console.info("  2 - Overwrite this file")
        console.info("  3 - Skip all remaining")
        console.info("  4 - Overwrite all remaining")
        choice = input("Enter option [1]: ").strip() or "1"

        if choice == "2":
            return "overwrite"
        if choice == "3":
            self._mode = ConflictMode.SKIP_ALL
            return "skip"
        if choice == "4":
            self._mode = ConflictMode.OVERWRITE_ALL
            return "overwrite"
        return "skip"


def run_decrypt_session(
    session: SessionInput,
    conflict_resolver: ConflictResolver,
    *,
    progress_fn: Callable[[int, int, str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> BatchResult:
    validate_vault_structure(session.vault_root)
    validate_output_writable(session.output_root)

    private_pem = load_user_private_pem(session.user_private_key_path)

    console.info("Scanning for encrypted MP4 files…")
    enc_paths = scan_cenc_mp4(session.input_root)
    db_paths = scan_plain_db_files(session.input_root)
    console.info(
        f"Found {len(enc_paths)} encrypted MP4 file(s) "
        f"and {len(db_paths)} plain .db file(s)."
    )

    if not enc_paths:
        db_copied = 0
        if not db_paths:
            console.summary(succeeded=0, failed=0, skipped=0, db_copied=0)
            return BatchResult(total=0, succeeded=0, failed=0, skipped=0)
        db_result = copy_plain_db_files(
            db_paths,
            input_root=session.input_root,
            output_root=session.output_root,
            conflict_resolver=conflict_resolver,
        )
        db_copied = db_result.copied
        console.summary(succeeded=0, failed=0, skipped=0, db_copied=db_copied)
        return BatchResult(total=0, succeeded=0, failed=0, skipped=0)

    console.info(f"Running preflight check on {len(enc_paths)} file(s)…")
    for index, mp4_path in enumerate(enc_paths, start=1):
        console.info(f"Preflight [{index}/{len(enc_paths)}]: {mp4_path.name}")
        preflight_cenc_mp4(mp4_path, session.vault_root, private_pem)

    batch_result = run_batch(
        enc_paths,
        vault_root=session.vault_root,
        private_pem=private_pem,
        input_root=session.input_root,
        output_root=session.output_root,
        conflict_resolver=conflict_resolver,
        progress_fn=progress_fn,
        cancel_check=cancel_check,
    )

    db_copied: int | None = None
    if batch_result.failed == 0 and db_paths:
        db_result = copy_plain_db_files(
            db_paths,
            input_root=session.input_root,
            output_root=session.output_root,
            conflict_resolver=conflict_resolver,
        )
        db_copied = db_result.copied

    console.summary(
        succeeded=batch_result.succeeded,
        failed=batch_result.failed,
        skipped=batch_result.skipped,
        db_copied=db_copied,
    )
    failures = [
        (o.mp4_path.name, o.message or "Unknown error")
        for o in batch_result.outcomes
        if o.status == "failed"
    ]
    console.print_failures(failures)
    return batch_result


def _run_session(session: SessionInput, conflict_resolver: ConflictResolver) -> int:
    run_decrypt_session(session, conflict_resolver)
    return 0


def interactive_main() -> int:
    init_customer_logging()
    console.info("Robocap CENC Video Decrypt")

    while True:
        try:
            session = collect_session_input()
            cfg = CustomerConfig.load(session.vault_root) or CustomerConfig(
                customer_id=None,
                vault_root=session.vault_root,
                user_private_key_path=session.user_private_key_path,
            )
            cfg.user_private_key_path = session.user_private_key_path
            cfg.vault_root = session.vault_root
            cfg.save(session.vault_root)
            return _run_session(session, InteractiveConflictResolver())
        except CustomerFacingError as exc:
            console.error(exc.message)
            retry = input("Try again? (Y/n): ").strip().lower()
            if retry in ("n", "no"):
                return 1
        except KeyboardInterrupt:
            console.info("")
            console.info("Operation cancelled.")
            return 130
