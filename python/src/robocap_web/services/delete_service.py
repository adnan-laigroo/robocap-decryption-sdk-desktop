from __future__ import annotations

from pathlib import Path

from robocap_customer.delete_prompts import DeleteSessionInput, run_delete
from robocap_customer.error_mapper import MSG_CUSTOMER_NOT_FOUND, MSG_NO_VERSIONS, CustomerFacingError
from robocap_customer.key_bundle import validate_customer_id_input
from robocap_customer.vault_validator import validate_vault_structure
from robocap_sdk.services.rsa_delete import DeleteRsaResult
from robocap_sdk.vault.key_vault import KeyVault

PUBLIC_PEM = "public.pem"
PRIVATE_PEM = "private.pem"


class DeleteService:
    def list_folders(self, vault_root: Path, customer_id: str) -> list[dict]:
        validate_customer_id_input(customer_id)
        root = vault_root.expanduser().resolve()
        validate_vault_structure(root)
        vault = KeyVault(root)
        if not vault.exists_customer(customer_id.strip()):
            raise CustomerFacingError(MSG_CUSTOMER_NOT_FOUND)
        key_dirs = vault.list_rsa_key_dirs(customer_id.strip())
        valid = [
            d for d in key_dirs
            if (d / PUBLIC_PEM).is_file() and (d / PRIVATE_PEM).is_file()
        ]
        if not valid:
            raise CustomerFacingError(MSG_NO_VERSIONS)
        folders = []
        cid = customer_id.strip()
        for index, key_dir in enumerate(valid, start=1):
            folders.append(
                {
                    "index": index,
                    "label": f"{cid}/rsa/{key_dir.name}",
                    "folder_name": key_dir.name,
                }
            )
        return folders

    def run_delete(
        self,
        vault_root: Path,
        customer_id: str,
        folder_name: str,
    ) -> DeleteRsaResult:
        validate_customer_id_input(customer_id)
        root = vault_root.expanduser().resolve()
        vault = KeyVault(root)
        key_dirs = vault.list_rsa_key_dirs(customer_id.strip())
        selected = next((d for d in key_dirs if d.name == folder_name), None)
        if selected is None:
            raise CustomerFacingError(MSG_NO_VERSIONS)
        session = DeleteSessionInput(
            vault_root=root,
            customer_id=customer_id.strip(),
            key_dir=selected,
        )
        return run_delete(session)
