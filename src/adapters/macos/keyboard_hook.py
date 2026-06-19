from collections.abc import Callable
import logging
from typing import Any

from adapters.inputs.captured_event import CapturedKeyEvent
from adapters.macos.event_tap import RawMacKeyEvent
from adapters.macos.keymap import key_event_from_macos
from application.input.results import AppKeyEventResult, KeyboardPipelineResult
from interop.key.key_event import KeyEvent

_logger = logging.getLogger(__name__)


class MacOSKeyboardCapture:
    def __init__(self, *, manager: Any) -> None:
        self._manager = manager
        self._listener: Callable[[CapturedKeyEvent], KeyboardPipelineResult] | None = None
        self._registered = False

    @property
    def running(self) -> bool:
        return self._registered

    def set_listener(self, listener: Callable[[CapturedKeyEvent], KeyboardPipelineResult]) -> None:
        self._listener = listener

    def start(self) -> None:
        _logger.debug(
            "MacOSKeyboardCapture.start manager_running=%s",
            self._manager.running,
        )
        self._manager.set_keyboard_listener(self._handle_raw_event)
        try:
            self._manager.start()
            self._registered = True
            _logger.debug("MacOSKeyboardCapture.start completed")
        except Exception:
            self._manager.set_keyboard_listener(None)
            raise

    def stop(self) -> None:
        _logger.debug(
            "MacOSKeyboardCapture.stop manager_running=%s",
            self._manager.running,
        )
        self._manager.set_keyboard_listener(None)
        self._manager.stop()
        self._registered = False
        _logger.debug("MacOSKeyboardCapture.stop completed")

    def _handle_raw_event(self, event: RawMacKeyEvent) -> KeyboardPipelineResult:
        if self._listener is None:
            return KeyboardPipelineResult(send_to_system=True, app_result=AppKeyEventResult.UNHANDLED)
        key_event = key_event_from_macos(
            key_code=event.key_code,
            pressed=event.pressed,
            is_repeat=event.is_repeat,
        )
        if key_event is None:
            return KeyboardPipelineResult(send_to_system=True, app_result=AppKeyEventResult.UNHANDLED)
        return self._listener(
            CapturedKeyEvent(
                key_event=key_event,
                native_context=None,
            )
        )
