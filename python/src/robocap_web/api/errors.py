from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AppError(Exception):
    code: str
    message_key: str
    message_params: dict[str, Any] | None = None
    status_code: int = 400

    def __post_init__(self) -> None:
        if self.message_params is None:
            self.message_params = {}
