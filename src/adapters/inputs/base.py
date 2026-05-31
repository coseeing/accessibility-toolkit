from collections.abc import Callable
from typing import Protocol

from remote_core.models.keys import KeyEvent


class InputCapture(Protocol):
    def set_listener(self, listener: Callable[[KeyEvent], None]) -> None: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...
