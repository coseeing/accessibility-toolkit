from collections.abc import Callable
from enum import StrEnum
from typing import Protocol

from interop.key.key_event import KeyEvent


class KeyEventDecision(StrEnum):
    PASS_THROUGH = "pass_through"
    SUPPRESS = "suppress"


class InputCapture(Protocol):
    @property
    def running(self) -> bool: ...

    def set_listener(
        self,
        listener: Callable[[KeyEvent], KeyEventDecision],
    ) -> None: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...


class HotkeyCapture(Protocol):
    @property
    def running(self) -> bool: ...

    def set_handler(self, handler: Callable[[], None]) -> None: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...
