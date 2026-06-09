from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from robocap_web.adapters.error_codes import map_exception
from robocap_web import app_state as app_state_module
from robocap_web.api.errors import AppError
from robocap_web.api.routes import auth, customers, decrypt, delete, import_, local
from robocap_web.auth.middleware import AuthMiddleware
from robocap_web.config import Settings, get_settings


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message_key": exc.message_key,
                "message_params": exc.message_params or {},
            }
        },
    )


async def generic_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    mapped = map_exception(exc)
    return await app_error_handler(_request, mapped)


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = app_state_module.get_app_state()
    await state.decrypt_service.start()
    yield
    await state.decrypt_service.stop()


def create_app(settings: Settings | None = None) -> FastAPI:
    app_state_module.app_state = app_state_module.build_app_state(settings)

    app = FastAPI(title="Robocap Web", lifespan=lifespan)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    cfg = app_state_module.get_app_state().settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        AuthMiddleware,
        settings=cfg,
        auth=app_state_module.get_app_state().auth,
    )

    @app.get("/api/health")
    def health() -> dict:
        return {
            "data": {
                "status": "ok",
                "dev_mode": cfg.dev_mode,
                "web_mode": cfg.web_mode,
            }
        }

    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(customers.router, prefix="/api/customers", tags=["customers"])
    app.include_router(import_.router, prefix="/api/import", tags=["import"])
    app.include_router(delete.router, prefix="/api/delete", tags=["delete"])
    app.include_router(decrypt.router, prefix="/api/decrypt", tags=["decrypt"])
    app.include_router(local.router, prefix="/api/local", tags=["local"])

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("robocap_web.main:app", host="0.0.0.0", port=8000, reload=True)
