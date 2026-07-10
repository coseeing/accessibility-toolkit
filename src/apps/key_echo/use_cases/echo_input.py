from collections.abc import Callable
import logging

from accessibility_toolkit.input import AppKeyEventResult
from accessibility_toolkit.input import HID
from accessibility_toolkit.input.events import KeyEvent
from accessibility_toolkit.output.speech import SpeechSequence

_logger = logging.getLogger(__name__)


class KeyEchoInputUseCase:
    def __init__(
        self,
        *,
        cancel: Callable[[], None],
        speak: Callable[[SpeechSequence], None],
    ) -> None:
        self._cancel = cancel
        self._speak = speak

    def handle(self, event: KeyEvent) -> AppKeyEventResult:
        if event.pressed:
            _logger.debug(
                "KeyEchoInput.handle pressed usage=0x%02X page=0x%02X -> cancel then speak",
                event.usage,
                event.usage_page,
            )
            self._cancel()
            self._speak(
                SpeechSequence(
                    items=(f"HID 0x{event.usage_page:02X}:0x{event.usage:02X}",)
                )
            )
        if event.usage_page == HID.KEYBOARD_PAGE and event.usage == HID.NUM_LOCK:
            return AppKeyEventResult.HANDLED_CONTINUE
        return AppKeyEventResult.HANDLED_STOP
