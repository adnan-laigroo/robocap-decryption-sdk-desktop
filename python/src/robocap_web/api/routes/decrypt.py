from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from robocap_web.adapters.error_codes import map_exception
from robocap_web.api.deps import get_app_state
from robocap_web.api.errors import AppError
from robocap_web.auth.deps import get_current_user
from robocap_web.auth.provider import User
from robocap_web.app_state import AppState

router = APIRouter()


class ScanRequest(BaseModel):
    input_root: str


class PreflightRequest(BaseModel):
    vault_path: str
    user_private_key_path: str
    input_root: str


class DecryptRunRequest(BaseModel):
    vault_path: str
    user_private_key_path: str
    input_root: str
    output_root: str
    customer_id: str | None = None


class ConflictRequest(BaseModel):
    decision: str


@router.post("/scan")
def scan(body: ScanRequest, state: AppState = Depends(get_app_state)) -> dict:
    from pathlib import Path

    files = state.decrypt_service.scan(Path(body.input_root))
    return {"data": {"files": files}}


@router.post("/preflight")
def preflight(body: PreflightRequest, state: AppState = Depends(get_app_state)) -> dict:
    from pathlib import Path

    try:
        data = state.decrypt_service.preflight(
            Path(body.vault_path),
            Path(body.user_private_key_path),
            Path(body.input_root),
        )
        return {"data": data}
    except Exception as exc:
        raise map_exception(exc) from exc


@router.post("/run")
async def run_decrypt(
    body: DecryptRunRequest,
    user: User = Depends(get_current_user),
    state: AppState = Depends(get_app_state),
) -> dict:
    from pathlib import Path

    from robocap_customer.prompts import SessionInput

    session = SessionInput(
        vault_root=Path(body.vault_path),
        user_private_key_path=Path(body.user_private_key_path),
        input_root=Path(body.input_root),
        output_root=Path(body.output_root),
    )
    try:
        record = await state.decrypt_service.enqueue(
            user["user_id"], session, body.customer_id
        )
        return {"data": record.to_public()}
    except AppError:
        raise
    except Exception as exc:
        raise map_exception(exc) from exc


@router.get("/tasks/{task_id}")
def get_task(task_id: str, state: AppState = Depends(get_app_state)) -> dict:
    record = state.decrypt_service.get_task(task_id)
    if record is None:
        raise AppError("task_not_found", "errors.task.notFound", status_code=404)
    return {"data": record.to_public()}


@router.get("/tasks/{task_id}/events")
async def task_events(task_id: str, state: AppState = Depends(get_app_state)):
    from fastapi.responses import StreamingResponse

    record = state.decrypt_service.get_task(task_id)
    if record is None:
        raise AppError("task_not_found", "errors.task.notFound", status_code=404)

    async def event_generator():
        for payload in state.sse.recent_events(task_id):
            yield state.sse.format_sse(payload)
        async for payload in state.sse.subscribe(task_id):
            yield state.sse.format_sse(payload)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/tasks/{task_id}/conflict")
def submit_conflict(
    task_id: str,
    body: ConflictRequest,
    state: AppState = Depends(get_app_state),
) -> dict:
    state.decrypt_service.submit_conflict(task_id, body.decision)
    return {"data": {"ok": True}}


@router.get("/tasks")
def list_tasks(
    user: User = Depends(get_current_user),
    state: AppState = Depends(get_app_state),
) -> dict:
    records = state.task_store.list_recent(user["user_id"])
    return {"data": [r.to_public() for r in records]}
