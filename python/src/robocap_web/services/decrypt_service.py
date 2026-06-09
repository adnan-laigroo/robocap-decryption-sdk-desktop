from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from robocap_customer.error_mapper import CustomerFacingError
from robocap_customer.preflight import preflight_cenc_mp4
from robocap_customer.prompts import SessionInput, run_decrypt_session
from robocap_customer.scanner import scan_cenc_mp4
from robocap_customer.vault_validator import load_user_private_pem

from robocap_web.adapters.conflict import ApiConflictResolver
from robocap_web.adapters.error_codes import map_exception
from robocap_web.adapters.progress import SseProgressReporter
from robocap_web.api.errors import AppError
from robocap_web.config import Settings
from robocap_web.tasks.models import TaskRecord, TaskStatus
from robocap_web.tasks.sse_hub import SseHub
from robocap_web.tasks.store import TaskStore


class DecryptService:
    def __init__(
        self,
        settings: Settings,
        store: TaskStore,
        sse: SseHub,
    ) -> None:
        self._settings = settings
        self._store = store
        self._sse = sse
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._running_by_user: dict[str, str | None] = {}
        self._conflicts: dict[str, ApiConflictResolver] = {}
        self._worker_task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._dispatch_loop())

    async def stop(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    def scan(self, input_root: Path) -> list[dict]:
        paths = scan_cenc_mp4(input_root)
        return [{"name": p.name, "path": str(p)} for p in paths]

    def preflight(
        self,
        vault_root: Path,
        user_private_key_path: Path,
        input_root: Path,
    ) -> dict:
        private_pem = load_user_private_pem(user_private_key_path)
        files = scan_cenc_mp4(input_root)
        results = []
        can_start = True
        for mp4 in files:
            try:
                preflight_cenc_mp4(mp4, vault_root, private_pem)
                results.append({"name": mp4.name, "status": "ok"})
            except CustomerFacingError as exc:
                can_start = False
                mapped = map_exception(exc)
                results.append(
                    {
                        "name": mp4.name,
                        "status": "failed",
                        "error": {
                            "code": mapped.code,
                            "message_key": mapped.message_key,
                            "message_params": mapped.message_params or {},
                        },
                    }
                )
        return {"can_start": can_start, "files": results}

    async def enqueue(
        self,
        user_id: str,
        session: SessionInput,
        customer_id: str | None,
    ) -> TaskRecord:
        pending = sum(
            1
            for rec in self._store.list_recent(user_id, limit=100)
            if rec.task_type == "decrypt"
            and rec.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
        )
        if pending >= self._settings.decrypt_max_pending_per_user:
            raise AppError("task_queue_full", "errors.task.queueFull")

        enc_paths = scan_cenc_mp4(session.input_root)
        if len(enc_paths) > self._settings.decrypt_max_mp4_per_task:
            raise AppError("task_too_large", "errors.task.tooLarge")

        record = TaskRecord(
            user_id=user_id,
            customer_id=customer_id,
            task_type="decrypt",
            status=TaskStatus.PENDING,
            total=len(enc_paths),
            meta={
                "vault_root": str(session.vault_root),
                "user_private_key_path": str(session.user_private_key_path),
                "input_root": str(session.input_root),
                "output_root": str(session.output_root),
            },
        )
        self._store.save(record)
        self._session_cache = getattr(self, "_session_cache", {})
        self._session_cache[record.task_id] = session
        await self._queue.put(record.task_id)
        return record

    _session_cache: dict[str, SessionInput]

    def get_task(self, task_id: str) -> TaskRecord | None:
        return self._store.load(task_id)

    def submit_conflict(self, task_id: str, decision: str) -> None:
        resolver = self._conflicts.get(task_id)
        if resolver is None:
            raise AppError("task_not_found", "errors.task.notFound", status_code=404)
        resolver.submit(decision)

    async def _dispatch_loop(self) -> None:
        while True:
            task_id = await self._queue.get()
            record = self._store.load(task_id)
            if record is None:
                continue
            if self._running_by_user.get(record.user_id):
                await self._queue.put(task_id)
                await asyncio.sleep(0.5)
                continue
            self._running_by_user[record.user_id] = task_id
            try:
                await asyncio.to_thread(self._run_decrypt_task, task_id)
            finally:
                self._running_by_user[record.user_id] = None

    def _run_decrypt_task(self, task_id: str) -> None:
        record = self._store.load(task_id)
        if record is None:
            return
        session = self._session_cache.get(task_id)
        if session is None:
            session = SessionInput(
                vault_root=Path(record.meta["vault_root"]),
                user_private_key_path=Path(record.meta["user_private_key_path"]),
                input_root=Path(record.meta["input_root"]),
                output_root=Path(record.meta["output_root"]),
            )

        record.status = TaskStatus.RUNNING
        record.touch()
        self._store.save(record)

        resolver = ApiConflictResolver(task_id, self._store, self._sse)
        self._conflicts[task_id] = resolver
        progress = SseProgressReporter(task_id, self._store, self._sse)

        def cancel_check() -> bool:
            rec = self._store.load(task_id)
            return bool(rec and rec.cancel_requested)

        try:
            batch = run_decrypt_session(
                session,
                resolver,
                progress_fn=progress.callback,
                cancel_check=cancel_check,
            )
            record = self._store.load(task_id)
            if record is None:
                return
            record.succeeded = batch.succeeded
            record.failed = batch.failed
            record.skipped = batch.skipped
            record.current_index = batch.total
            record.status = TaskStatus.COMPLETED
            record.finished_at = datetime.now(timezone.utc)
            record.touch()
            self._store.save(record)
            self._sse.emit(
                task_id,
                "summary",
                {
                    "status": record.status.value,
                    "succeeded": batch.succeeded,
                    "failed": batch.failed,
                    "skipped": batch.skipped,
                },
            )
        except Exception as exc:
            mapped = map_exception(exc)
            record = self._store.load(task_id)
            if record:
                record.status = TaskStatus.FAILED
                record.error = {
                    "code": mapped.code,
                    "message_key": mapped.message_key,
                }
                record.finished_at = datetime.now(timezone.utc)
                record.touch()
                self._store.save(record)
                self._sse.emit(task_id, "error", record.error)
        finally:
            self._conflicts.pop(task_id, None)
            self._session_cache.pop(task_id, None)
