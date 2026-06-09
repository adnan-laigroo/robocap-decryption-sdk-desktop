from __future__ import annotations

import json
from pathlib import Path

from robocap_web.storage.paths import TenantPathResolver
from robocap_web.tasks.models import TaskRecord


class TaskStore:
    def __init__(self, paths: TenantPathResolver) -> None:
        self._paths = paths

    def save(self, record: TaskRecord) -> None:
        record.touch()
        path = self._paths.task_file(record.task_id)
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        self._append_index(record)

    def load(self, task_id: str) -> TaskRecord | None:
        path = self._paths.task_file(task_id)
        if not path.is_file():
            return None
        return TaskRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def _append_index(self, record: TaskRecord) -> None:
        index_path = self._paths.user_task_index(record.user_id)
        entries: list[dict] = []
        if index_path.is_file():
            try:
                entries = json.loads(index_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                entries = []
        entries = [e for e in entries if e.get("task_id") != record.task_id]
        entries.append(
            {
                "task_id": record.task_id,
                "task_type": record.task_type,
                "status": record.status.value,
                "created_at": record.created_at.isoformat(),
            }
        )
        index_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    def list_recent(self, user_id: str, limit: int = 20) -> list[TaskRecord]:
        index_path = self._paths.user_task_index(user_id)
        if not index_path.is_file():
            return []
        try:
            entries = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        records: list[TaskRecord] = []
        for entry in reversed(entries[-limit:]):
            rec = self.load(entry["task_id"])
            if rec:
                records.append(rec)
        return records
