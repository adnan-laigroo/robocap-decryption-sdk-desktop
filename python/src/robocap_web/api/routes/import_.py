from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from robocap_web.adapters.error_codes import map_exception
from robocap_web.api.deps import get_app_state
from robocap_web.app_state import AppState

router = APIRouter()


class AnalyzeBundleRequest(BaseModel):
    bundle_path: str


class GenerateKeysRequest(BaseModel):
    bundle_path: str
    layout: Literal["direct", "subfolder"] = "subfolder"


class ImportRunRequest(BaseModel):
    vault_path: str
    customer_id: str
    bundle_path: str
    user_private_key_path: str | None = None


@router.post("/analyze-bundle")
def analyze_bundle(body: AnalyzeBundleRequest, state: AppState = Depends(get_app_state)) -> dict:
    from pathlib import Path

    try:
        data = state.import_service.analyze_bundle(Path(body.bundle_path))
        return {"data": data}
    except Exception as exc:
        raise map_exception(exc) from exc


@router.post("/generate-keys")
def generate_keys(body: GenerateKeysRequest, state: AppState = Depends(get_app_state)) -> dict:
    from pathlib import Path

    try:
        out = state.import_service.generate_keys(Path(body.bundle_path), body.layout)
        return {"data": out}
    except Exception as exc:
        raise map_exception(exc) from exc


@router.post("/run")
def run_import(body: ImportRunRequest, state: AppState = Depends(get_app_state)) -> dict:
    from pathlib import Path

    try:
        data = state.import_service.run_import(
            vault_root=Path(body.vault_path),
            customer_id=body.customer_id,
            bundle_path=Path(body.bundle_path),
            user_private_key_path=(
                Path(body.user_private_key_path) if body.user_private_key_path else None
            ),
        )
        return {"data": data}
    except Exception as exc:
        raise map_exception(exc) from exc
