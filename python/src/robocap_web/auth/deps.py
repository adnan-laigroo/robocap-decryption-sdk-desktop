from __future__ import annotations

from fastapi import Request

from robocap_web.auth.provider import User


def get_current_user(request: Request) -> User:
    return request.state.user
