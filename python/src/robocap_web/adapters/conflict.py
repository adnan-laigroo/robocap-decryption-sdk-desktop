from __future__ import annotations

import asyncio
import threading
from typing import Literal

from robocap_customer.conflict_resolver import ConflictMode

from robocap_web.tasks.models import TaskRecord, TaskStatus
from robocap_web.tasks.sse_hub import SseHub
from robocap_web.tasks.store import TaskStore


class ApiConflictResolver:
    """Thread-safe conflict resolver for worker thread + async API."""

    def __init__(
        self,
        task_id: str,
        store: TaskStore,
        sse: SseHub,
    ) -> None:
        self._task_id = task_id
        self._store = store
        self._sse = sse
        self._mode = ConflictMode.ASK
        self._event = threading.Event()
        self._decision: Literal["skip", "overwrite"] | None = None

    def resolve(self, relative_target: str) -> Literal["skip", "overwrite"]:
        if self._mode == ConflictMode.SKIP_ALL:
            return "skip"
        if self._mode == ConflictMode.OVERWRITE_ALL:
            return "overwrite"

        record = self._store.load(self._task_id)
        if record:
            record.status = TaskStatus.AWAITING_CONFLICT
            record.touch()
            self._store.save(record)

        self._sse.emit(
            self._task_id,
            "conflict",
            {"relative_target": relative_target, "awaiting": True},
        )

        self._event.clear()
        self._decision = None
        if not self._event.wait(timeout=600):
            return "skip"

        return self._decision or "skip"

    def submit(self, decision: str) -> None:
        if decision in ("skip_all", "skip"):
            if decision == "skip_all":
                self._mode = ConflictMode.SKIP_ALL
            self._decision = "skip"
        elif decision in ("overwrite_all", "overwrite"):
            if decision == "overwrite_all":
                self._mode = ConflictMode.OVERWRITE_ALL
            self._decision = "overwrite"
        else:
            self._decision = "skip"

        record = self._store.load(self._task_id)
        if record and record.status == TaskStatus.AWAITING_CONFLICT:
            record.status = TaskStatus.RUNNING
            record.touch()
            self._store.save(record)
        self._event.set()
