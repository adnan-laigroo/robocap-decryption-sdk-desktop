from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import click

from robocap_sdk.errors import RobocapError
from robocap_sdk.models.key_meta import RsaKeyMeta
from robocap_sdk.services.decrypt_cenc import decrypt_cenc_mp4
from robocap_sdk.services.rsa_delete import delete_rsa_key_version
from robocap_sdk.services.rsa_import import import_rsa_key_version


def _emit_json(data: dict) -> None:
    click.echo(json.dumps(data, default=str))


def _handle_error(exc: Exception) -> None:
    if isinstance(exc, RobocapError):
        click.echo(json.dumps(exc.to_dict()), err=True)
        sys.exit(1)
    raise exc


@click.group()
def cli() -> None:
    """Robocap CENC MP4 decryption SDK."""


@cli.command("import-rsa")
@click.option("--customer-id", required=True)
@click.option("--public-key", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--private-key", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--rsa-key-version", type=int, required=True)
@click.option("--rsa-bits", type=click.Choice(["2048", "4096"]), default="2048")
@click.option("--device-id", default="")
@click.option("--effective-at", default=None, help="ISO8601; default now UTC")
@click.option("--sdk-root", type=click.Path(path_type=Path), default=None)
def cmd_import_rsa(
    customer_id: str,
    public_key: Path,
    private_key: Path,
    rsa_key_version: int,
    rsa_bits: str,
    device_id: str,
    effective_at: str | None,
    sdk_root: Path | None,
) -> None:
    """Import an RSA key pair into the vault for CENC CEK unwrap."""
    try:
        eff = (
            datetime.fromisoformat(effective_at.replace("Z", "+00:00"))
            if effective_at
            else datetime.now(timezone.utc)
        )
        meta = RsaKeyMeta(
            rsa_key_version=rsa_key_version,
            effective_at=eff,
            device_id=device_id or customer_id,
            rsa_bits=int(rsa_bits),
        )
        result = import_rsa_key_version(
            customer_id,
            public_key.read_bytes(),
            private_key.read_bytes(),
            meta,
            sdk_root=sdk_root,
        )
        _emit_json(
            {
                "status": "ok",
                "customer_id": result.customer_id,
                "rsa_key_version": result.rsa_key_version,
                "vault_rsa_dir": str(result.vault_rsa_dir),
            }
        )
    except Exception as exc:
        _handle_error(exc)


@cli.command("delete-rsa")
@click.option("--customer-id", required=True)
@click.option("--rsa-key-version", type=int, required=True)
@click.option("--sdk-root", type=click.Path(path_type=Path), default=None)
def cmd_delete_rsa(
    customer_id: str,
    rsa_key_version: int,
    sdk_root: Path | None,
) -> None:
    """Delete one RSA key version from the vault."""
    try:
        result = delete_rsa_key_version(
            customer_id,
            rsa_key_version,
            sdk_root=sdk_root,
        )
        _emit_json(
            {
                "status": "ok",
                "customer_id": result.customer_id,
                "rsa_key_version": rsa_key_version,
                "folder_name": result.folder_name,
            }
        )
    except Exception as exc:
        _handle_error(exc)


@cli.command("decrypt-cenc")
@click.option("--mp4-path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--private-key", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--output-dir", type=click.Path(path_type=Path), required=True)
@click.option("--sdk-root", type=click.Path(path_type=Path), default=None)
@click.option("--ffmpeg", "ffmpeg_executable", default=None, help="Path to ffmpeg")
@click.option("--ffprobe", "ffprobe_executable", default=None, help="Path to ffprobe")
def cmd_decrypt_cenc(
    mp4_path: Path,
    private_key: Path,
    output_dir: Path,
    sdk_root: Path | None,
    ffmpeg_executable: str | None,
    ffprobe_executable: str | None,
) -> None:
    """Decrypt a CENC MP4 (RSA-OAEP CEK unwrap + ffmpeg)."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        result = decrypt_cenc_mp4(
            mp4_path,
            private_key.read_bytes(),
            output_dir,
            sdk_root=sdk_root,
            ffmpeg_executable=ffmpeg_executable,
            ffprobe_executable=ffprobe_executable,
        )
        _emit_json(
            {
                "status": "ok",
                "output_path": str(result.output_path),
                "customer_id": result.customer_id,
                "rsa_key_version": result.rsa_key_version,
                "kid_hex": result.kid_hex,
            }
        )
    except Exception as exc:
        _handle_error(exc)


if __name__ == "__main__":
    cli()
