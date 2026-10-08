#!/usr/bin/env python3
"""Unattended bulk CENC decrypt over a directory tree, using the SDK key vault.

Multi-device by design: each file's owning device and RSA key version come from
that file's own tags, resolved by the SDK rules (``cenc_customer_id`` then
``deviceid``, and the ``host`` tag for ``robowrist_*`` files). Keys are never
brute-forced across devices.

Prerequisite - import every device's key versions into the vault once:

    robocap-decryption-sdk import-rsa --customer-id DEVICE_ID \\
      --public-key rsa_public_spki.pem --private-key rsa_private_pkcs8.pem \\
      --rsa-key-version 1

Then run one unattended sweep over the footage:

    ./bulk_decrypt.py --root /mnt/footage --output-dir /mnt/plain --workers 16
    ./bulk_decrypt.py --root /mnt/footage --in-place --workers 16

Safe to interrupt. Every file is recorded in the done-file as it finishes and
re-runs skip finished work. Nothing replaces an original until the decrypted
copy passes validation, and the replacement itself is atomic.

The work is a stream copy, so it is disk bound rather than CPU bound: start at
``--workers 16`` on SSD/NVMe and 4-8 on a spinning disk or a network share.

Note on ownership: this feeds the vault's own private key into the SDK
ownership check, which makes that check self-satisfying here. The tool assumes
whoever runs it is the legitimate holder of the vault.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from robocap_decryption_sdk import RobocapError, decrypt_cenc_mp4
from robocap_decryption_sdk.config import DEFAULT_SDK_ROOT, keys_vault_root
from robocap_decryption_sdk.io.ffmpeg_cli import resolve_ffprobe_executable
from robocap_decryption_sdk.io.mp4_cenc import (
    parse_cenc_metadata_from_tags,
    read_format_tags,
)
from robocap_decryption_sdk.vault.key_vault import KeyVault

CEK_TAG = "cenc_cek_wrapped_b64"
SIZE_TOLERANCE = 0.05
SIZE_FLOOR_BYTES = 1 << 20  # remuxing rewrites the moov; small files move more than 5%
TMP_PREFIX = ".robocap-decrypt-"
PROGRESS_EVERY = 200

_print_lock = threading.Lock()
_done_lock = threading.Lock()
_pem_lock = threading.Lock()
_counts_lock = threading.Lock()

counts = {"decrypted": 0, "already_plain": 0, "unreadable": 0, "failed": 0}
_pem_cache: dict[str, bytes] = {}


def log(message: str) -> None:
    with _print_lock:
        print(message, flush=True)


def bump(key: str) -> None:
    with _counts_lock:
        counts[key] += 1


def record(done_path: Path, rel: str, outcome: str, detail: str) -> None:
    # Keep each result on one line so full subprocess diagnostics remain
    # readable in both the GUI log and the resumable done-file.
    detail = " ".join(detail.split())
    with _done_lock:
        with open(done_path, "a", encoding="utf-8") as handle:
            handle.write(f"{rel}\t{outcome}\t{detail}\n")


def report(done_path: Path, rel: str, outcome: str, detail: str = "") -> None:
    detail = " ".join(detail.split())
    record(done_path, rel, outcome, detail)
    message = f"{outcome.upper()}: {rel}"
    if detail:
        message += f" — {detail}"
    log(message)


def load_done(done_path: Path) -> set[str]:
    """Relative paths already settled. Failures are left out so they retry."""
    done: set[str] = set()
    if not done_path.is_file():
        return done
    with open(done_path, encoding="utf-8") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2 and parts[1] != "failed":
                done.add(parts[0])
    return done


def ownership_pem(vault: KeyVault, customer_id: str) -> bytes:
    """Vault private key for the device; satisfies the SDK ownership check."""
    with _pem_lock:
        cached = _pem_cache.get(customer_id)
    if cached is not None:
        return cached
    version = vault.get_latest_rsa_version(customer_id)
    pem = vault.private_pem(customer_id, version).read_bytes()
    with _pem_lock:
        _pem_cache[customer_id] = pem
    return pem


def probe_duration(path: Path) -> float:
    exe = resolve_ffprobe_executable()
    try:
        result = subprocess.run(
            [exe, "-v", "error", "-show_format", "-print_format", "json", str(path)],
            capture_output=True,
            check=False,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 0.0
    if result.returncode != 0:
        return 0.0
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return 0.0


def validate_output(out_path: Path, in_size: int) -> str | None:
    """Return a reason string when the decrypted file looks wrong, else None."""
    duration = probe_duration(out_path)
    if duration <= 0:
        return "validation: decrypted file has no readable duration"
    out_size = out_path.stat().st_size
    delta = abs(out_size - in_size)
    if delta > SIZE_FLOOR_BYTES and delta / in_size > SIZE_TOLERANCE:
        return f"validation: size {out_size} against input {in_size}"
    return None


def process(
    path: Path,
    root: Path,
    vault: KeyVault,
    vault_root: Path,
    output_root: Path | None,
    done_path: Path,
) -> None:
    rel = str(path.relative_to(root))
    try:
        try:
            tags = read_format_tags(path)
        except RobocapError as exc:
            # Preserve the actual ffprobe/tag parser diagnostic. The old
            # generic "truncated file" message hid unrelated failures too.
            report(
                done_path,
                rel,
                "unreadable",
                f"{exc.code.name}: {exc.message}",
            )
            bump("unreadable")
            return

        if not tags.get(CEK_TAG):
            # Decrypt strips this tag, so a file without it is already plaintext.
            report(done_path, rel, "already_plain")
            bump("already_plain")
            return

        meta = parse_cenc_metadata_from_tags(tags, mp4_path=path)
        pem = ownership_pem(vault, meta.customer_id)
        in_size = path.stat().st_size

        if output_root is not None:
            dest_dir = output_root / path.parent.relative_to(root)
            result = decrypt_cenc_mp4(
                path, pem, dest_dir, metadata=meta, sdk_root=vault_root
            )
            problem = validate_output(result.output_path, in_size)
            if problem is not None:
                result.output_path.unlink(missing_ok=True)
                report(done_path, rel, "failed", problem)
                bump("failed")
                return
        else:
            # Stage beside the original so the replace stays on one filesystem.
            staging = Path(tempfile.mkdtemp(dir=path.parent, prefix=TMP_PREFIX))
            try:
                result = decrypt_cenc_mp4(
                    path, pem, staging, metadata=meta, sdk_root=vault_root
                )
                problem = validate_output(result.output_path, in_size)
                if problem is not None:
                    report(done_path, rel, "failed", problem)
                    bump("failed")
                    return
                os.replace(result.output_path, path)
            finally:
                shutil.rmtree(staging, ignore_errors=True)

        report(
            done_path,
            rel,
            "decrypted",
            f"{meta.customer_id} v{result.rsa_key_version}",
        )
        bump("decrypted")
    except RobocapError as exc:
        report(done_path, rel, "failed", f"{exc.code.name}: {exc.message}")
        bump("failed")
    except Exception as exc:  # keep one bad file from stopping the sweep
        report(done_path, rel, "failed", f"{type(exc).__name__}: {exc}")
        bump("failed")


def scan(root: Path, done: set[str]) -> list[Path]:
    todo: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() != ".mp4" or not path.is_file():
            continue
        if path.name.startswith("._"):  # macOS metadata stub
            continue
        rel_parts = path.relative_to(root).parts
        if any(part.startswith(TMP_PREFIX) for part in rel_parts):
            continue  # leftovers from an interrupted in-place run
        if str(path.relative_to(root)) in done:
            continue
        todo.append(path)
    return todo


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bulk-decrypt CENC MP4s across devices using the SDK vault."
    )
    parser.add_argument("--root", type=Path, required=True, help="Folder to scan.")
    parser.add_argument(
        "--sdk-root",
        type=Path,
        default=DEFAULT_SDK_ROOT,
        help="Vault root (default: %(default)s).",
    )
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument(
        "--output-dir", type=Path, help="Mirror the tree here and keep the originals."
    )
    destination.add_argument(
        "--in-place", action="store_true", help="Replace originals after validation."
    )
    parser.add_argument(
        "--workers", type=int, default=8, help="Files in flight (default: %(default)s)."
    )
    parser.add_argument("--done-file", type=Path, default=Path("decrypt_done.txt"))
    parser.add_argument(
        "--dry-run", action="store_true", help="Report what would run, change nothing."
    )
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"--root is not a directory: {root}", file=sys.stderr)
        return 1

    vault_root = args.sdk_root.expanduser().resolve()
    if not keys_vault_root(vault_root).is_dir():
        print(f"No vault keys under {keys_vault_root(vault_root)}", file=sys.stderr)
        print("Import each device's keys first with `import-rsa`.", file=sys.stderr)
        return 1
    vault = KeyVault(vault_root)

    output_root = args.output_dir.expanduser().resolve() if args.output_dir else None
    if output_root is not None and (output_root == root or root in output_root.parents):
        print("--output-dir must sit outside --root", file=sys.stderr)
        return 1

    done_path = args.done_file.expanduser().resolve()
    done = load_done(done_path)
    todo = scan(root, done)
    log(f"{len(todo)} file(s) to process ({len(done)} already recorded as done).")
    if args.dry_run or not todo:
        return 0

    started = time.time()
    workers = max(1, args.workers)
    processed = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(process, path, root, vault, vault_root, output_root, done_path)
            for path in todo
        ]
        for _ in as_completed(futures):
            processed += 1
            if processed % PROGRESS_EVERY and processed != len(todo):
                continue
            elapsed = time.time() - started
            rate = processed / elapsed if elapsed else 0.0
            eta = (len(todo) - processed) / rate / 60 if rate else 0.0
            log(
                f"  {processed}/{len(todo)}  decrypted={counts['decrypted']} "
                f"plain={counts['already_plain']} unreadable={counts['unreadable']} "
                f"failed={counts['failed']}  {rate:.1f} files/s  ETA {eta:.0f} min"
            )

    log("-" * 62)
    log(f"  decrypted            : {counts['decrypted']}")
    log(f"  already plaintext    : {counts['already_plain']}")
    log(f"  skipped (unreadable) : {counts['unreadable']}")
    log(f"  FAILED               : {counts['failed']}")
    log(f"  elapsed              : {(time.time() - started) / 60:.1f} min")
    log("-" * 62)
    if counts["failed"]:
        log(f"Failures are listed in {done_path}.")
        log("ERR_CUSTOMER_NOT_FOUND or ERR_RSA_NOT_IMPORTED means that device has no")
        log("keys in the vault; ERR_CENC_CEKA_TRIAL_FAILED means the key version that")
        log("recorded the file is missing. Import the missing keys, then re-run:")
        log("failed files are retried automatically.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
