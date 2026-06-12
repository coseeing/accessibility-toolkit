from collections.abc import Callable

from adapters.inputs.base import KeyEventDecision
from interop.key.key_event import KeyEvent


class ActiveKeyEventPolicy:
    def __init__(
        self,
        *,
        exit_usage: int,
        on_exit: Callable[[], KeyEventDecision],
        on_key: Callable[[KeyEvent], KeyEventDecision],
    ) -> None:
        self._exit_usage = exit_usage
        self._on_exit = on_exit
        self._on_key = on_key

    def handle(self, event: KeyEvent) -> KeyEventDecision:
        if event.pressed and event.usage == self._exit_usage:
            return self._on_exit()
        return self._on_key(event)
