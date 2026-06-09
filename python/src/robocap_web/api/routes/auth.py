from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from robocap_web.api.deps import get_app_state
from robocap_web.api.errors import AppError
from robocap_web.auth.deps import get_current_user
from robocap_web.auth.provider import User
from robocap_web.app_state import AppState

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest, state: AppState = Depends(get_app_state)) -> Response:
    user = state.auth.authenticate(body.username, body.password)
    if user is None:
        raise AppError("unauthorized", "errors.auth.unauthorized", status_code=401)
    session_id = state.auth.create_session(user)
    import json

    response = Response(
        content=json.dumps({"data": user}),
        media_type="application/json",
    )
    response.set_cookie(key="robocap_session", value=session_id, httponly=True, samesite="lax")
    return response


@router.get("/me")
def me(user: User = Depends(get_current_user), state: AppState = Depends(get_app_state)) -> dict:
    return {
        "data": {
            "user_id": user["user_id"],
            "username": user["username"],
            "dev_mode": state.settings.dev_mode,
        }
    }


@router.post("/logout")
def logout() -> dict:
    return {"data": {"ok": True}}
