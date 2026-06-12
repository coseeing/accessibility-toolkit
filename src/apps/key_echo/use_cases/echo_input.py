from collections.abc import Callable

from adapters.inputs.base import KeyEventDecision
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

    def handle(self, event: KeyEvent) -> KeyEventDecision:
        if event.pressed:
            self._cancel()
            self._speak(
                SpeechSequence(
                    items=(f"HID 0x{event.usage_page:02X}:0x{event.usage:02X}",)
                )
            )
        return KeyEventDecision.SUPPRESS
