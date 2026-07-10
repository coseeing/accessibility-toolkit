from collections.abc import Callable

from accessibility_toolkit.input.events import CapturedKeyEvent, KeyEvent
from accessibility_toolkit.input.hid import HID
from accessibility_toolkit.input.results import AppKeyEventResult


class ActiveKeyEventPolicy:
    def __init__(
        self,
        *,
        exit_usage: int,
        on_exit: Callable[[], AppKeyEventResult],
        on_key: Callable[[KeyEvent], AppKeyEventResult],
    ) -> None:
        self._exit_usage = exit_usage
        self._on_exit = on_exit
        self._on_key = on_key

    def handle(self, event: KeyEvent) -> AppKeyEventResult:
        if event.pressed and event.usage == self._exit_usage:
            return self._on_exit()
        return self._on_key(event)


def should_pass_through_system_toggle(event: CapturedKeyEvent) -> bool:
    from accessibility_toolkit.input.windows.native_key_context import WindowsNativeKeyContext

    return (
        event.key_event.usage == HID.NUM_LOCK
        and isinstance(event.native_context, WindowsNativeKeyContext)
    )
