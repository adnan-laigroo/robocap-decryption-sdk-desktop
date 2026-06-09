#!/usr/bin/env python3
"""Generate CENC-compatible 2048-bit RSA key pair (SPKI public + PKCS#8 private)."""

from __future__ import annotations

import argparse
from pathlib import Path

from robocap_customer.key_bundle import GENERATED_FILE_NAMES
from robocap_customer.key_generate import generate_cenc_key_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("generated_keys_cenc_2048"),
        help="Directory to write PEM files (default: ./generated_keys_cenc_2048)",
    )
    parser.add_argument(
        "--also-user-private",
        action="store_true",
        help="Also write user_private.pem (for robocap-customer-decrypt)",
    )
    args = parser.parse_args()
    out = generate_cenc_key_bundle(
        args.output_dir,
        include_user_private=args.also_user_private,
    )
    print(f"Output directory: {out}")
    for name in GENERATED_FILE_NAMES:
        if name == "user_private.pem" and not args.also_user_private:
            continue
        print(f"  {name}")


if __name__ == "__main__":
    main()
