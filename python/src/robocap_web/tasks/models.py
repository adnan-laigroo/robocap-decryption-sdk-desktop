from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_CONFLICT = "awaiting_conflict"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskRecord(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    customer_id: str | None = None
    task_type: Literal["import", "decrypt"]
    status: TaskStatus = TaskStatus.PENDING
    total: int = 0
    current_index: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    cancel_requested: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    error: dict[str, Any] | None = None
    meta: dict[str, Any] = Field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    def to_public(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "customer_id": self.customer_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "total": self.total,
            "current_index": self.current_index,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "skipped": self.skipped,
            "cancel_requested": self.cancel_requested,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
            "meta": self.meta,
        }
