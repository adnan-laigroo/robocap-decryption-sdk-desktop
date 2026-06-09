#!/usr/bin/env python3
"""Import a 2048-bit RSA key pair into the SDK vault for CENC decrypt."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

from robocap_sdk.models.key_meta import RsaKeyMeta
from robocap_sdk.services.rsa_import import import_rsa_key_version


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--customer-id", required=True)
    parser.add_argument("--public-pem", type=Path, required=True)
    parser.add_argument("--private-pem", type=Path, required=True)
    parser.add_argument(
        "--sdk-root",
        type=Path,
        default=Path(os.environ.get("SDK_ROOT", Path.home() / "robocap-vault")),
    )
    parser.add_argument("--rsa-key-version", type=int, default=1)
    parser.add_argument("--device-id", default=None)
    args = parser.parse_args()

    public_pem = args.public_pem.expanduser().resolve().read_bytes()
    private_pem = args.private_pem.expanduser().resolve().read_bytes()
    sdk_root = args.sdk_root.expanduser().resolve()
    device_id = args.device_id or args.customer_id

    result = import_rsa_key_version(
        args.customer_id,
        public_pem,
        private_pem,
        RsaKeyMeta(
            rsa_key_version=args.rsa_key_version,
            effective_at=datetime.now(timezone.utc),
            device_id=device_id,
            rsa_bits=2048,
        ),
        sdk_root=sdk_root,
    )
    print(f"OK: imported v{result.rsa_key_version}")
    print(f"Vault: {result.vault_rsa_dir}")


if __name__ == "__main__":
    main()
