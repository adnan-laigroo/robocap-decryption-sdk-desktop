from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from robocap_decryption_sdk.models.key_meta import RsaKeyMeta
from robocap_decryption_sdk.services.rsa_import import ImportRsaResult, import_rsa_key_version

from robocap_customer.device_keys import (
    register_user_private_version,
    vault_user_private_path,
    vault_user_private_path_for_version,
)
from robocap_customer import console
from robocap_customer.bootstrap import init_customer_logging
from robocap_customer.config import CustomerConfig
from robocap_customer.error_mapper import (
    CustomerFacingError,
    MSG_GEN_CANCELLED,
    MSG_GEN_FAILED,
    to_import_message,
)
from robocap_customer.key_bundle import (
    CENC_RSA_BITS,
    GENERATED_FILE_NAMES,
    BundlePathKind,
    analyze_bundle_path,
    default_user_private_path,
    load_key_bundle,
    validate_customer_id_input,
)
from robocap_customer.key_generate import generate_cenc_key_bundle
from robocap_customer.vault_bootstrap import (
    assert_vault_writable,
    ensure_vault_layout,
    next_rsa_version,
)

DEFAULT_VAULT_HINT = Path.home() / "robocap-vault"


@dataclass
class ImportSessionInput:
    vault_root: Path
    customer_id: str
    key_bundle_dir: Path
    user_private_key_path: Path


def _default_vault_path() -> str:
    candidate = DEFAULT_VAULT_HINT
    if candidate.is_dir():
        loaded = CustomerConfig.load(candidate)
        if loaded:
            return str(loaded.vault_root)
    return str(candidate)


def _prompt_text(label: str, default: str | None = None) -> str:
    while True:
        if default:
            raw = input(f"{label} [{default}]: ").strip()
            value = raw or default
        else:
            value = input(f"{label}: ").strip()
        if value:
            return value
        console.error("Value cannot be empty. Please try again.")


def _prompt_vault_path(default: str | None = None) -> Path:
    while True:
        raw_default = default or _default_vault_path()
        value = _prompt_text("Vault path", default=raw_default)
        return Path(value).expanduser().resolve()


def _prompt_yes_no(prompt: str, *, default_yes: bool = True) -> bool:
    suffix = " (Y/n): " if default_yes else " (y/N): "
    raw = input(prompt + suffix).strip().lower()
    if not raw:
        return default_yes
    return raw in ("y", "yes")


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


def _generate_keys_in_dir(target: Path) -> Path:
    try:
        out = generate_cenc_key_bundle(target, include_user_private=True)
    except OSError as exc:
        raise CustomerFacingError(MSG_GEN_FAILED) from exc
    console.info(f"Keys generated successfully in {out}.")
    for name in GENERATED_FILE_NAMES:
        console.info(f"  {name}")
    return out


def _offer_generate_keys(target: Path) -> Path:
    if not _prompt_yes_no(
        "No key files found. Generate a new 2048-bit key pair here?"
    ):
        raise CustomerFacingError(MSG_GEN_CANCELLED)
    return _generate_keys_in_dir(target)


def _pick_bundle(candidates: list[Path]) -> Path:
    console.info("Multiple key bundles found:")
    for index, candidate in enumerate(candidates, start=1):
        console.info(f"  {index} - {candidate}")
    while True:
        raw = input("Select bundle [1]: ").strip() or "1"
        try:
            choice = int(raw)
        except ValueError:
            console.error("Invalid selection. Please try again.")
            continue
        if 1 <= choice <= len(candidates):
            return candidates[choice - 1]
        console.error("Invalid selection. Please try again.")


def _resolve_key_bundle_directory(raw_path: Path) -> Path:
    path = raw_path.expanduser()
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        console.info(f"Directory created: {path.resolve()}")

    analysis = analyze_bundle_path(path)
    if analysis.kind is BundlePathKind.DIRECT:
        return analysis.path
    if analysis.kind is BundlePathKind.SINGLE_CHILD:
        console.info(f"Using key bundle: {analysis.path}")
        return analysis.path
    if analysis.kind is BundlePathKind.MULTIPLE_CHILDREN:
        return _pick_bundle(list(analysis.candidates))

    return _offer_generate_keys(path.resolve())


def _prompt_key_bundle_directory() -> Path:
    while True:
        value = _prompt_text("Key bundle directory")
        try:
            return _resolve_key_bundle_directory(Path(value))
        except CustomerFacingError:
            raise


def collect_import_input() -> ImportSessionInput:
    vault_root = _prompt_vault_path()
    loaded = CustomerConfig.load(vault_root) if vault_root.is_dir() else None
    customer_default = loaded.customer_id if loaded and loaded.customer_id else None

    customer_id = _prompt_text("Customer ID", default=customer_default)
    validate_customer_id_input(customer_id)
    customer_id = customer_id.strip()

    key_bundle_dir = _prompt_key_bundle_directory()

    user_key = default_user_private_path(key_bundle_dir)
    if user_key is not None:
        user_private_key_path = user_key
    else:
        user_private_key_path = _prompt_file_path("User private key PEM path")

    return ImportSessionInput(
        vault_root=vault_root,
        customer_id=customer_id,
        key_bundle_dir=key_bundle_dir,
        user_private_key_path=user_private_key_path,
    )


def run_import(session: ImportSessionInput) -> ImportRsaResult:
    assert_vault_writable(session.vault_root)
    vault_root = ensure_vault_layout(session.vault_root)
    bundle = load_key_bundle(session.key_bundle_dir)
    version = next_rsa_version(vault_root, session.customer_id)

    result = import_rsa_key_version(
        session.customer_id,
        bundle.public_pem,
        bundle.private_pem,
        RsaKeyMeta(
            rsa_key_version=version,
            effective_at=datetime.now(timezone.utc),
            device_id=session.customer_id,
            rsa_bits=CENC_RSA_BITS,
        ),
        sdk_root=vault_root,
    )

    version_pem = vault_user_private_path_for_version(
        vault_root, session.customer_id, result.rsa_key_version
    )
    version_pem.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(session.user_private_key_path, version_pem)
    register_user_private_version(vault_root, session.customer_id, result.rsa_key_version)

    legacy_pem = vault_user_private_path(vault_root, session.customer_id)
    legacy_pem.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(session.user_private_key_path, legacy_pem)

    cfg = CustomerConfig(
        customer_id=session.customer_id,
        vault_root=vault_root,
        user_private_key_path=session.user_private_key_path,
    )
    cfg.save(vault_root)
    return result


def _vault_rsa_label(customer_id: str, rsa_key_version: int) -> str:
    return f"{customer_id}/rsa/v{rsa_key_version}"


def _print_success(result: ImportRsaResult) -> None:
    label = _vault_rsa_label(result.customer_id, result.rsa_key_version)
    console.info(
        f"Imported key folder {label} for customer {result.customer_id}."
    )
    console.info("You can now run robocap-customer-decrypt to decrypt videos.")


def import_main() -> int:
    init_customer_logging()
    console.info("Robocap CENC Vault Import")

    while True:
        try:
            session = collect_import_input()
            result = run_import(session)
            _print_success(result)
            return 0
        except CustomerFacingError as exc:
            console.error(exc.message)
            retry = input("Try again? (Y/n): ").strip().lower()
            if retry in ("n", "no"):
                return 1
        except Exception as exc:
            console.error(to_import_message(exc))
            retry = input("Try again? (Y/n): ").strip().lower()
            if retry in ("n", "no"):
                return 1
        except KeyboardInterrupt:
            console.info("")
            console.info("Operation cancelled.")
            return 130
