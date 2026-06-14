from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

from adapters.inputs.captured_event import CapturedKeyEvent

if TYPE_CHECKING:
    from application.input.results import KeyboardPipelineResult


class KeyEventDecision(StrEnum):
    PASS_THROUGH = "pass_through"
    SUPPRESS = "suppress"


class InputCapture(Protocol):
    @property
    def running(self) -> bool: ...

    def set_listener(
        self,
        listener: Callable[[CapturedKeyEvent], KeyboardPipelineResult],
    ) -> None: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...


class HotkeyCapture(Protocol):
    @property
    def running(self) -> bool: ...

    def set_handler(self, handler: Callable[[], None]) -> None: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...
