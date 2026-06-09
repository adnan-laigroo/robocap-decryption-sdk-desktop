from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from robocap_customer.import_prompts import ImportSessionInput, run_import
from robocap_customer.key_bundle import (
    BundlePathKind,
    analyze_bundle_path,
    default_user_private_path,
    next_version_subdir_name,
    resolve_key_generate_dir,
    validate_customer_id_input,
)
from robocap_customer.key_generate import generate_cenc_key_bundle
from robocap_customer.error_mapper import MSG_GEN_FAILED, CustomerFacingError


class ImportService:
    def analyze_bundle(self, bundle_path: Path) -> dict:
        analysis = analyze_bundle_path(bundle_path)
        kind = analysis.kind.value
        candidates = [
            {"path": str(p), "label": str(p)} for p in analysis.candidates
        ]
        resolved = None
        if analysis.kind == BundlePathKind.DIRECT:
            resolved = str(analysis.path)
        elif analysis.kind == BundlePathKind.SINGLE_CHILD:
            resolved = str(analysis.path)
        parent = bundle_path.expanduser().resolve()
        next_subfolder = next_version_subdir_name(parent)
        return {
            "kind": kind,
            "candidates": candidates,
            "resolved_path": resolved,
            "next_subfolder": next_subfolder,
        }

    def generate_keys(self, bundle_path: Path, layout: str = "subfolder") -> dict:
        if layout not in ("direct", "subfolder"):
            raise CustomerFacingError(MSG_GEN_FAILED)
        try:
            target = resolve_key_generate_dir(bundle_path, layout)
            out = generate_cenc_key_bundle(target, include_user_private=True)
            return {
                "path": str(out),
                "layout": layout,
                "folder_name": out.name if layout == "subfolder" else None,
            }
        except FileExistsError as exc:
            raise CustomerFacingError(MSG_GEN_FAILED) from exc
        except OSError as exc:
            raise CustomerFacingError(MSG_GEN_FAILED) from exc

    def run_import(
        self,
        *,
        vault_root: Path,
        customer_id: str,
        bundle_path: Path,
        user_private_key_path: Path | None,
    ) -> dict:
        validate_customer_id_input(customer_id)
        bundle_dir = bundle_path.expanduser().resolve()
        user_key = default_user_private_path(bundle_dir)
        if user_key is not None:
            resolved_user = user_key
        elif user_private_key_path is not None:
            resolved_user = user_private_key_path.expanduser().resolve()
        else:
            raise CustomerFacingError(
                "User private key PEM path is required when bundle has no user_private.pem."
            )

        session = ImportSessionInput(
            vault_root=vault_root.expanduser().resolve(),
            customer_id=customer_id.strip(),
            key_bundle_dir=bundle_dir,
            user_private_key_path=resolved_user,
        )
        result = run_import(session)
        return {
            "customer_id": result.customer_id,
            "rsa_key_version": result.rsa_key_version,
            "label": f"{result.customer_id}/rsa/v{result.rsa_key_version}",
        }
