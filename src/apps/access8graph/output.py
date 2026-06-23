from collections.abc import Iterable
from typing import Protocol

from application.output import Capabilities
from interop.speech.speech_commands import BreakCommand
from interop.speech.speech_sequence import SpeechSequence


class FlowOutput(Protocol):
    def cancel_speech(self) -> None: ...
    def speak(self, items: Iterable[object]) -> None: ...
    def beep_failure(self) -> None: ...


class Access8GraphFlowOutput:
    def __init__(self, capabilities: Capabilities) -> None:
        self._capabilities = capabilities

    def cancel_speech(self) -> None:
        self._capabilities.speech.cancel()

    def speak(self, items: Iterable[object]) -> None:
        filtered = tuple(str(item) for item in items if item)
        if not filtered:
            return
        sequence_items: list[object] = []
        for index, item in enumerate(filtered):
            if index > 0:
                sequence_items.append(BreakCommand(time=1))
            sequence_items.append(item)
        self._capabilities.speech.speak(SpeechSequence(items=tuple(sequence_items)))

    def beep_failure(self) -> None:
        tone = self._capabilities.tone
        if tone is None:
            return
        beep = getattr(tone, "beep", None)
        if callable(beep):
            beep(100, 100)
