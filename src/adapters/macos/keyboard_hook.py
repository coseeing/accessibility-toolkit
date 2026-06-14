from collections.abc import Callable
from typing import Any

from adapters.inputs.base import KeyEventDecision
from adapters.inputs.captured_event import CapturedKeyEvent
from adapters.macos.event_tap import RawMacKeyEvent
from adapters.macos.keymap import key_event_from_macos
from interop.key.key_event import KeyEvent


class MacOSKeyboardCapture:
    def __init__(self, *, manager: Any) -> None:
        self._manager = manager
        self._listener: Callable[[CapturedKeyEvent], KeyEventDecision] | None = None

    @property
    def running(self) -> bool:
        return bool(self._manager.running)

    def set_listener(self, listener: Callable[[CapturedKeyEvent], KeyEventDecision]) -> None:
        self._listener = listener

    def start(self) -> None:
        self._manager.set_keyboard_listener(self._handle_raw_event)
        try:
            self._manager.start()
        except Exception:
            self._manager.set_keyboard_listener(None)
            raise

    def stop(self) -> None:
        self._manager.set_keyboard_listener(None)
        self._manager.stop()

    def _handle_raw_event(self, event: RawMacKeyEvent) -> KeyEventDecision:
        if self._listener is None:
            return KeyEventDecision.PASS_THROUGH
        key_event = key_event_from_macos(
            key_code=event.key_code,
            pressed=event.pressed,
            is_repeat=event.is_repeat,
        )
        if key_event is None:
            return KeyEventDecision.PASS_THROUGH
        return self._listener(
            CapturedKeyEvent(
                key_event=key_event,
                native_context=None,
            )
        )
