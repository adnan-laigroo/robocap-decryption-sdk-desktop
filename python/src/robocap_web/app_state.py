from __future__ import annotations

from dataclasses import dataclass

from robocap_web.auth.provider import SessionAuthProvider
from robocap_web.config import Settings, get_settings
from robocap_web.services.customer_service import CustomerService
from robocap_web.services.decrypt_service import DecryptService
from robocap_web.services.delete_service import DeleteService
from robocap_web.services.import_service import ImportService
from robocap_web.storage.paths import TenantPathResolver
from robocap_web.tasks.sse_hub import SseHub
from robocap_web.tasks.store import TaskStore


@dataclass
class AppState:
    settings: Settings
    auth: SessionAuthProvider
    paths: TenantPathResolver
    task_store: TaskStore
    sse: SseHub
    import_service: ImportService
    delete_service: DeleteService
    customer_service: CustomerService
    decrypt_service: DecryptService


app_state: AppState | None = None


def build_app_state(settings: Settings | None = None) -> AppState:
    settings = settings or get_settings()
    paths = TenantPathResolver(settings)
    store = TaskStore(paths)
    sse = SseHub(buffer_size=settings.sse_event_buffer_size)
    decrypt_service = DecryptService(settings, store, sse)
    return AppState(
        settings=settings,
        auth=SessionAuthProvider(settings),
        paths=paths,
        task_store=store,
        sse=sse,
        import_service=ImportService(),
        delete_service=DeleteService(),
        customer_service=CustomerService(),
        decrypt_service=decrypt_service,
    )


def get_app_state() -> AppState:
    if app_state is None:
        raise RuntimeError("Application state is not initialized")
    return app_state
