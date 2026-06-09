from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from robocap_sdk.services.rsa_delete import DeleteRsaResult, delete_rsa_key_dir
from robocap_sdk.vault.key_vault import KeyVault

from robocap_customer import console
from robocap_customer.bootstrap import init_customer_logging
from robocap_customer.config import CustomerConfig
from robocap_customer.error_mapper import (
    MSG_CUSTOMER_NOT_FOUND,
    MSG_NO_VERSIONS,
    MSG_VAULT_BAD,
    CustomerFacingError,
    to_delete_message,
)
from robocap_customer.key_bundle import validate_customer_id_input
from robocap_customer.vault_bootstrap import assert_vault_writable
from robocap_customer.vault_validator import validate_vault_structure

DEFAULT_VAULT_HINT = Path.home() / "robocap-vault"


@dataclass
class DeleteSessionInput:
    vault_root: Path
    customer_id: str
    key_dir: Path


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


def _prompt_vault_path() -> Path:
    while True:
        value = _prompt_text("Vault path", default=_default_vault_path())
        path = Path(value).expanduser().resolve()
        if not path.is_dir():
            console.error(MSG_VAULT_BAD)
            continue
        try:
            validate_vault_structure(path)
        except CustomerFacingError:
            console.error(MSG_VAULT_BAD)
            continue
        return path


def _key_dir_label(customer_id: str, key_dir: Path) -> str:
    return f"{customer_id}/rsa/{key_dir.name}"


def _pick_key_dir(customer_id: str, candidates: list[Path]) -> Path:
    console.info("Key version folders found:")
    for index, candidate in enumerate(candidates, start=1):
        console.info(f"  {index} - {_key_dir_label(customer_id, candidate)}")
    while True:
        raw = input("Select folder to delete [1]: ").strip() or "1"
        try:
            choice = int(raw)
        except ValueError:
            console.error("Invalid selection. Please try again.")
            continue
        if 1 <= choice <= len(candidates):
            return candidates[choice - 1]
        console.error("Invalid selection. Please try again.")


def _confirm_delete(folder_name: str) -> bool:
    answer = input(f"Type yes to delete {folder_name}: ").strip().lower()
    return answer == "yes"


def collect_delete_input() -> DeleteSessionInput | None:
    vault_root = _prompt_vault_path()
    loaded = CustomerConfig.load(vault_root)
    customer_default = loaded.customer_id if loaded and loaded.customer_id else None

    customer_id = _prompt_text("Customer ID", default=customer_default)
    validate_customer_id_input(customer_id)
    customer_id = customer_id.strip()

    vault = KeyVault(vault_root)
    if not vault.exists_customer(customer_id):
        raise CustomerFacingError(MSG_CUSTOMER_NOT_FOUND)

    key_dirs = vault.list_rsa_key_dirs(customer_id)
    if not key_dirs:
        raise CustomerFacingError(MSG_NO_VERSIONS)

    selected = _pick_key_dir(customer_id, key_dirs)

    if not _confirm_delete(_key_dir_label(customer_id, selected)):
        console.info("Delete cancelled.")
        return None

    return DeleteSessionInput(
        vault_root=vault_root,
        customer_id=customer_id,
        key_dir=selected,
    )


def run_delete(session: DeleteSessionInput) -> DeleteRsaResult:
    assert_vault_writable(session.vault_root)
    validate_vault_structure(session.vault_root)
    return delete_rsa_key_dir(
        session.customer_id,
        session.key_dir,
        sdk_root=session.vault_root,
    )


def _print_success(result: DeleteRsaResult) -> None:
    console.info(
        f"Deleted key folder {result.folder_name} "
        f"for customer {result.customer_id}."
    )


def delete_main() -> int:
    init_customer_logging()
    console.info("Robocap CENC Vault Delete")

    while True:
        try:
            session = collect_delete_input()
            if session is None:
                return 0
            result = run_delete(session)
            _print_success(result)
            return 0
        except CustomerFacingError as exc:
            console.error(exc.message)
            retry = input("Try again? (Y/n): ").strip().lower()
            if retry in ("n", "no"):
                return 1
        except Exception as exc:
            console.error(to_delete_message(exc))
            retry = input("Try again? (Y/n): ").strip().lower()
            if retry in ("n", "no"):
                return 1
        except KeyboardInterrupt:
            console.info("")
            console.info("Operation cancelled.")
            return 130
