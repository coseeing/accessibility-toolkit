from collections.abc import Callable

from adapters.inputs.base import KeyEventDecision
from interop.key.key_event import KeyEvent


class ActiveKeyEventPolicy:
    def __init__(
        self,
        *,
        exit_vk: int,
        on_exit: Callable[[], KeyEventDecision],
        on_key: Callable[[KeyEvent], KeyEventDecision],
    ) -> None:
        self._exit_vk = exit_vk
        self._on_exit = on_exit
        self._on_key = on_key

    def handle(self, event: KeyEvent) -> KeyEventDecision:
        if event.pressed and event.vk == self._exit_vk:
            return self._on_exit()
        return self._on_key(event)
