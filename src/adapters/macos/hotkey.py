from collections.abc import Callable
from typing import Any

from adapters.macos.event_tap import RawMacKeyEvent


F11_KEY_CODE = 103


class MacOSHotkeyCapture:
    def __init__(self, *, manager: Any, key_code: int = F11_KEY_CODE) -> None:
        self._manager = manager
        self._handler: Callable[[], None] | None = None
        self._key_code = key_code

    @property
    def running(self) -> bool:
        return bool(self._manager.running)

    def set_handler(self, handler: Callable[[], None]) -> None:
        self._handler = handler

    def start(self) -> None:
        self._manager.set_hotkey_handler(self._handle_raw_event)
        try:
            self._manager.start()
        except Exception:
            self._manager.set_hotkey_handler(None)
            raise

    def stop(self) -> None:
        self._manager.set_hotkey_handler(None)
        self._manager.stop()

    def _handle_raw_event(self, event: RawMacKeyEvent) -> bool:
        if event.key_code != self._key_code:
            return False
        if not event.pressed:
            return False
        if event.is_repeat:
            return True
        if self._handler is not None:
            self._handler()
        return True
