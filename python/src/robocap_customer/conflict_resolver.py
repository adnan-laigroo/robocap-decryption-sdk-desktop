from __future__ import annotations

from enum import Enum
from typing import Literal, Protocol


class ConflictMode(Enum):
    ASK = "ask"
    SKIP_ALL = "skip_all"
    OVERWRITE_ALL = "overwrite_all"


class ConflictResolver(Protocol):
    def resolve(self, relative_target: str) -> Literal["skip", "overwrite"]: ...


class FixedConflictResolver:
    """Test helper: always skip or overwrite."""

    def __init__(self, decision: Literal["skip", "overwrite"]) -> None:
        self._decision = decision

    def resolve(self, relative_target: str) -> Literal["skip", "overwrite"]:
        return self._decision


class StatefulConflictResolver:
    """Test helper: first conflict uses prompt_fn, then applies mode."""

    def __init__(
        self,
        prompt_fn,
        *,
        initial_mode: ConflictMode = ConflictMode.ASK,
    ) -> None:
        self._prompt_fn = prompt_fn
        self._mode = initial_mode

    @property
    def mode(self) -> ConflictMode:
        return self._mode

    def resolve(self, relative_target: str) -> Literal["skip", "overwrite"]:
        if self._mode == ConflictMode.SKIP_ALL:
            return "skip"
        if self._mode == ConflictMode.OVERWRITE_ALL:
            return "overwrite"
        decision, new_mode = self._prompt_fn(relative_target)
        self._mode = new_mode
        return decision
