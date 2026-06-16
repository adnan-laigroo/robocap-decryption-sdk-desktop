from __future__ import annotations

from pathlib import Path

from robocap_customer.config import CustomerConfig
from robocap_decryption_sdk.vault.key_vault import KeyVault


class CustomerService:
    def list_customers(self, vault_root: Path) -> dict:
        root = vault_root.expanduser().resolve()
        vault = KeyVault(root)
        keys_root = root / "vault" / "keys"
        customers: list[dict] = []
        active = None
        cfg = CustomerConfig.load(root)
        if cfg and cfg.customer_id:
            active = cfg.customer_id
        if keys_root.is_dir():
            for child in sorted(keys_root.iterdir()):
                if not child.is_dir():
                    continue
                cid = child.name
                versions = vault.list_rsa_versions(cid)
                customers.append(
                    {
                        "customer_id": cid,
                        "versions": [f"v{v}" for v in versions],
                    }
                )
        return {"customers": customers, "active_customer_id": active}

    def set_active(self, vault_root: Path, customer_id: str) -> None:
        root = vault_root.expanduser().resolve()
        cfg = CustomerConfig.load(root) or CustomerConfig(
            customer_id=None,
            vault_root=root,
        )
        cfg.customer_id = customer_id.strip()
        cfg.vault_root = root
        cfg.save(root)
