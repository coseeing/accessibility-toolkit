from collections.abc import Callable
import logging
from typing import Any

from accessibility_toolkit.input.macos.event_tap import RawMacKeyEvent

_logger = logging.getLogger(__name__)


F11_KEY_CODE = 103


class MacOSHotkeyCapture:
    def __init__(self, *, manager: Any, key_code: int = F11_KEY_CODE) -> None:
        self._manager = manager
        self._handler: Callable[[], None] | None = None
        self._key_code = key_code
        self._registered = False

    @property
    def running(self) -> bool:
        return self._registered

    def set_handler(self, handler: Callable[[], None]) -> None:
        self._handler = handler

    def start(self) -> None:
        _logger.debug(
            "MacOSHotkeyCapture.start key_code=%s manager_running=%s",
            self._key_code,
            self._manager.running,
        )
        self._manager.set_hotkey_handler(self._handle_raw_event)
        try:
            self._manager.start()
            self._registered = True
        except Exception:
            self._manager.set_hotkey_handler(None)
            raise

    def stop(self) -> None:
        _logger.debug(
            "MacOSHotkeyCapture.stop key_code=%s manager_running=%s",
            self._key_code,
            self._manager.running,
        )
        self._manager.set_hotkey_handler(None)
        self._manager.stop()
        self._registered = False

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
