from collections.abc import Callable

from application.input.results import AppKeyEventResult
from interop.key import HID
from interop.key.key_event import KeyEvent
from interop.speech.speech_sequence import SpeechSequence


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
            self._cancel()
            self._speak(
                SpeechSequence(
                    items=(f"HID 0x{event.usage_page:02X}:0x{event.usage:02X}",)
                )
            )
        if event.usage_page == HID.KEYBOARD_PAGE and event.usage == HID.NUM_LOCK:
            return AppKeyEventResult.HANDLED_CONTINUE
        return AppKeyEventResult.HANDLED_STOP
