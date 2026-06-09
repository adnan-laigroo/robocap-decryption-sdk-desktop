from __future__ import annotations

from pathlib import Path

from robocap_sdk.vault.layout import ensure_private_dir

from robocap_customer.error_mapper import MSG_OUTPUT_PERM, MSG_VAULT_BAD, CustomerFacingError


def validate_vault_structure(vault_root: Path) -> None:
    root = vault_root.expanduser().resolve()
    if not root.is_dir():
        raise CustomerFacingError(MSG_VAULT_BAD)

    keys_root = root / "vault" / "keys"
    if not keys_root.is_dir():
        raise CustomerFacingError(MSG_VAULT_BAD)


def validate_output_writable(output_root: Path) -> None:
    root = output_root.expanduser().resolve()
    try:
        ensure_private_dir(root)
        probe = root / ".robocap_write_probe"
        probe.write_bytes(b"x")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        raise CustomerFacingError(MSG_OUTPUT_PERM) from exc


def load_user_private_pem(user_private_key_path: Path) -> bytes:
    path = user_private_key_path.expanduser().resolve()
    if not path.is_file():
        raise CustomerFacingError(MSG_VAULT_BAD)
    try:
        return path.read_bytes()
    except OSError as exc:
        raise CustomerFacingError(MSG_VAULT_BAD) from exc
