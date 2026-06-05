from collections.abc import Callable
from enum import StrEnum
from typing import Protocol

from remote_core.models.keys import KeyEvent


class KeyEventDecision(StrEnum):
    PASS_THROUGH = "pass_through"
    FORWARD_AND_SUPPRESS = "forward_and_suppress"
    LOCAL_ONLY_SUPPRESS = "local_only_suppress"


class InputCapture(Protocol):
    def set_listener(
        self,
        listener: Callable[[KeyEvent], KeyEventDecision],
    ) -> None: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...


class HotkeyCapture(Protocol):
    def set_handler(self, handler: Callable[[], None]) -> None: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...
