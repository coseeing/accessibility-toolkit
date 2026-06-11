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
            self._speak(SpeechSequence(items=(f"VK {event.vk}",)))
        return KeyEventDecision.SUPPRESS
