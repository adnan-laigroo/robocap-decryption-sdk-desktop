from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Sentinel defaults. Acceptable only for single-user localhost ("local") use;
# any non-local deployment MUST override them via env (see _reject_insecure_defaults).
_DEFAULT_WEB_PASSWORD = "123456"
_DEFAULT_SESSION_SECRET = "dev-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    dev_mode: bool = Field(default=False, alias="DEV_MODE")
    web_mode: str = Field(default="local", alias="ROBOCAP_WEB_MODE")
    data_root: Path = Field(
        default_factory=lambda: Path.cwd() / "data",
        alias="ROBOCAP_DATA_ROOT",
    )
    web_user: str = Field(default="frodobot", alias="ROBOCAP_WEB_USER")
    web_password: str = Field(default=_DEFAULT_WEB_PASSWORD, alias="ROBOCAP_WEB_PASSWORD")
    session_secret: str = Field(default=_DEFAULT_SESSION_SECRET, alias="ROBOCAP_SESSION_SECRET")
    decrypt_max_pending_per_user: int = Field(
        default=10, alias="ROBOCAP_DECRYPT_MAX_PENDING_PER_USER"
    )
    decrypt_max_mp4_per_task: int = Field(
        default=100, alias="ROBOCAP_DECRYPT_MAX_MP4_PER_TASK"
    )
    decrypt_file_timeout_sec: int = Field(
        default=1800, alias="ROBOCAP_DECRYPT_FILE_TIMEOUT_SEC"
    )
    task_retention_days: int = Field(default=90, alias="ROBOCAP_TASK_RETENTION_DAYS")
    sse_event_buffer_size: int = Field(default=50, alias="ROBOCAP_SSE_EVENT_BUFFER_SIZE")
    browse_roots: str = Field(default="", alias="ROBOCAP_BROWSE_ROOTS")

    @property
    def is_local(self) -> bool:
        return self.web_mode.lower() == "local"

    @model_validator(mode="after")
    def _reject_insecure_defaults(self) -> "Settings":
        # Localhost single-user mode may keep the sentinel defaults; any other
        # deployment must set a real password and session secret via env.
        if not self.is_local and not self.dev_mode:
            insecure = []
            if self.web_password == _DEFAULT_WEB_PASSWORD:
                insecure.append("ROBOCAP_WEB_PASSWORD")
            if self.session_secret == _DEFAULT_SESSION_SECRET:
                insecure.append("ROBOCAP_SESSION_SECRET")
            if insecure:
                raise ValueError(
                    "Insecure default(s) for non-local deployment: "
                    + ", ".join(insecure)
                    + ". Set them to strong, unique values via environment variables."
                )
        return self

    @property
    def browse_root_paths(self) -> list[Path]:
        if not self.browse_roots.strip():
            return [Path.home()]
        return [Path(p.strip()).expanduser().resolve() for p in self.browse_roots.split(";") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
