from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from robocap_web.api.deps import get_app_state
from robocap_web.api.errors import AppError
from robocap_web.app_state import AppState

router = APIRouter()


@router.get("/browse")
def browse(
    path: str = Query(default=""),
    state: AppState = Depends(get_app_state),
) -> dict:
    from pathlib import Path

    if not state.settings.dev_mode or not state.settings.is_local:
        raise AppError("forbidden", "errors.auth.forbidden", status_code=403)

    target = Path(path).expanduser() if path else state.settings.browse_root_paths[0]
    resolved = state.paths.is_allowed_browse(target)
    if not resolved.is_dir():
        raise AppError("not_found", "errors.common.notFound", status_code=404)

    entries = []
    for child in sorted(resolved.iterdir(), key=lambda p: p.name.lower()):
        if child.name.startswith("."):
            continue
        entries.append(
            {
                "name": child.name,
                "path": str(child),
                "is_dir": child.is_dir(),
            }
        )

    parent_path: str | None = None
    parent = resolved.parent
    if parent != resolved:
        try:
            state.paths.is_allowed_browse(parent)
            parent_path = str(parent)
        except PermissionError:
            parent_path = None

    return {"data": {"path": str(resolved), "parent": parent_path, "entries": entries}}
