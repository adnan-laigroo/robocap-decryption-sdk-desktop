from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from robocap_web.config import Settings


class User(TypedDict):
    user_id: str
    username: str


class TenantPathResolver:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def data_root(self) -> Path:
        root = self._settings.data_root.expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def user_root(self, user_id: str) -> Path:
        path = self.data_root() / "users" / user_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def tasks_dir(self) -> Path:
        path = self.data_root() / "tasks"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def task_file(self, task_id: str) -> Path:
        return self.tasks_dir() / f"{task_id}.json"

    def user_task_index(self, user_id: str) -> Path:
        return self.user_root(user_id) / "task_index.json"

    def assert_under_roots(self, path: Path, roots: list[Path]) -> Path:
        resolved = path.expanduser().resolve()
        for root in roots:
            try:
                resolved.relative_to(root)
                return resolved
            except ValueError:
                continue
        raise PermissionError(f"Path not allowed: {path}")

    def is_allowed_browse(self, path: Path) -> Path:
        return self.assert_under_roots(path, self._settings.browse_root_paths)
