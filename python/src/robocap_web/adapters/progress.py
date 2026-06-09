from __future__ import annotations

from robocap_web.tasks.models import TaskRecord
from robocap_web.tasks.sse_hub import SseHub
from robocap_web.tasks.store import TaskStore


class SseProgressReporter:
    def __init__(self, task_id: str, store: TaskStore, sse: SseHub) -> None:
        self._task_id = task_id
        self._store = store
        self._sse = sse

    def callback(self, current: int, total: int, message: str) -> None:
        record = self._store.load(self._task_id)
        if not record:
            return
        record.current_index = current
        record.total = total
        record.touch()
        self._store.save(record)
        filename = record.meta.get("current_filename", "")
        self._sse.emit(
            self._task_id,
            "progress",
            {
                "current": current,
                "total": total,
                "filename": filename,
                "message": message,
            },
        )
