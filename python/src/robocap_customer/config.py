from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

CONFIG_FILENAME = "customer_config.json"


@dataclass
class CustomerConfig:
    customer_id: str | None
    vault_root: Path
    user_private_key_path: Path | None = None

    @classmethod
    def load(cls, vault_root: Path) -> CustomerConfig | None:
        path = vault_root / CONFIG_FILENAME
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        vault_raw = data.get("vault_root")
        if not vault_raw:
            return None
        customer_id = data.get("customer_id")
        user_key_raw = data.get("user_private_key_path")
        return cls(
            customer_id=str(customer_id).strip() if customer_id else None,
            vault_root=Path(vault_raw).expanduser(),
            user_private_key_path=(
                Path(user_key_raw).expanduser() if user_key_raw else None
            ),
        )

    def save(self, vault_root: Path) -> None:
        payload: dict[str, str] = {
            "vault_root": str(self.vault_root.resolve()),
        }
        if self.customer_id:
            payload["customer_id"] = self.customer_id
        if self.user_private_key_path:
            payload["user_private_key_path"] = str(
                self.user_private_key_path.expanduser().resolve()
            )
        path = vault_root / CONFIG_FILENAME
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
