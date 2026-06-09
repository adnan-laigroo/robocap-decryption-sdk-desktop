from __future__ import annotations

import secrets
from typing import TypedDict

from robocap_web.config import Settings


class User(TypedDict):
    user_id: str
    username: str


class SessionAuthProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._sessions: dict[str, User] = {}

    def authenticate(self, username: str, password: str) -> User | None:
        if not secrets.compare_digest(username, self._settings.web_user):
            return None
        if not secrets.compare_digest(password, self._settings.web_password):
            return None
        return User(user_id=username, username=username)

    def create_session(self, user: User) -> str:
        session_id = secrets.token_urlsafe(32)
        self._sessions[session_id] = user
        return session_id

    def get_user_by_session(self, session_id: str) -> User | None:
        return self._sessions.get(session_id)

    def destroy_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
