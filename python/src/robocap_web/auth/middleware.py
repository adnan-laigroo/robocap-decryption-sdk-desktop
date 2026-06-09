from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from robocap_web.auth.provider import SessionAuthProvider, User
from robocap_web.config import Settings


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings, auth: SessionAuthProvider) -> None:
        super().__init__(app)
        self._settings = settings
        self._auth = auth

    async def dispatch(self, request: Request, call_next) -> Response:
        if self._settings.dev_mode:
            request.state.user = User(user_id="dev", username="dev")
            return await call_next(request)

        session_id = request.cookies.get("robocap_session")
        if session_id:
            user = self._auth.get_user_by_session(session_id)
            if user:
                request.state.user = user
                return await call_next(request)

        if request.url.path in ("/api/health", "/api/auth/login"):
            return await call_next(request)

        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "code": "unauthorized",
                    "message_key": "errors.auth.unauthorized",
                    "message_params": {},
                }
            },
        )
