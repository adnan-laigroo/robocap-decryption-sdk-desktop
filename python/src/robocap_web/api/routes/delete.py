from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from robocap_web.adapters.error_codes import map_exception
from robocap_web.api.deps import get_app_state
from robocap_web.api.errors import AppError
from robocap_web.app_state import AppState

router = APIRouter()


@router.get("/folders")
def list_folders(
    customer_id: str = Query(...),
    vault_path: str = Query(...),
    state: AppState = Depends(get_app_state),
) -> dict:
    from pathlib import Path

    try:
        folders = state.delete_service.list_folders(Path(vault_path), customer_id)
        return {"data": {"folders": folders}}
    except Exception as exc:
        raise map_exception(exc) from exc


class DeleteRunRequest(BaseModel):
    vault_path: str
    customer_id: str
    folder_name: str
    confirm: str


@router.post("/run")
def run_delete(body: DeleteRunRequest, state: AppState = Depends(get_app_state)) -> dict:
    from pathlib import Path

    if body.confirm != "yes":
        raise AppError("delete_cancelled", "errors.delete.cancelled")
    try:
        result = state.delete_service.run_delete(
            Path(body.vault_path),
            body.customer_id,
            body.folder_name,
        )
        return {
            "data": {
                "customer_id": result.customer_id,
                "folder_name": result.folder_name,
            }
        }
    except Exception as exc:
        raise map_exception(exc) from exc
