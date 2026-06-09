from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from robocap_web.adapters.error_codes import map_exception
from robocap_web.api.deps import get_app_state
from robocap_web.app_state import AppState

router = APIRouter()


@router.get("")
def list_customers(
    vault_path: str = Query(...),
    state: AppState = Depends(get_app_state),
) -> dict:
    from pathlib import Path

    return {"data": state.customer_service.list_customers(Path(vault_path))}


class ActiveCustomerRequest(BaseModel):
    vault_path: str
    customer_id: str


@router.put("/active")
def set_active(body: ActiveCustomerRequest, state: AppState = Depends(get_app_state)) -> dict:
    from pathlib import Path

    try:
        state.customer_service.set_active(Path(body.vault_path), body.customer_id)
        return {"data": {"customer_id": body.customer_id}}
    except Exception as exc:
        raise map_exception(exc) from exc
