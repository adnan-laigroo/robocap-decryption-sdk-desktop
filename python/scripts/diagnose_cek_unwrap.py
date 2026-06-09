#!/usr/bin/env python3
"""Try RSA-OAEP unwrap of cenc_cek_wrapped_b64 from an MP4 using a vault private key."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from robocap_sdk.crypto.rsa_oaep import unwrap_cek


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mp4-path", type=Path, required=True)
    parser.add_argument("--private-pem", type=Path, required=True)
    args = parser.parse_args()

    mp4 = args.mp4_path.expanduser().resolve()
    priv_path = args.private_pem.expanduser().resolve()
    if not mp4.is_file():
        print(f"MP4 not found: {mp4}", file=sys.stderr)
        return 1
    if not priv_path.is_file():
        print(f"Private key not found: {priv_path}", file=sys.stderr)
        return 1

    raw = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-print_format",
            "json",
            str(mp4),
        ]
    )
    tags = json.loads(raw.decode("utf-8"))["format"]["tags"]
    wrapped_b64 = tags.get("cenc_cek_wrapped_b64")
    if not wrapped_b64:
        print("MP4 missing cenc_cek_wrapped_b64 tag", file=sys.stderr)
        return 1

    wrapped = base64.b64decode(wrapped_b64, validate=True)
    customer = tags.get("cenc_customer_id") or tags.get("username") or "(unknown)"
    print(f"customer tag: {customer}")
    print(f"wrapped CEK length: {len(wrapped)} bytes")

    private_key = serialization.load_pem_private_key(priv_path.read_bytes(), password=None)
    print(f"private key bits: {private_key.key_size}")

    try:
        cek = unwrap_cek(wrapped, private_key)
    except Exception as exc:
        print("CEK unwrap FAILED -> vault private key does not match device public key")
        print(f"detail: {exc}")
        return 2

    print(f"CEK unwrap OK -> CEK length {len(cek)} bytes; decrypt-cenc should work")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
