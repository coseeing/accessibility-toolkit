from collections.abc import Iterable
from typing import Protocol

from accessibility_toolkit.output import SpeechOutputPort, ToneOutput
from accessibility_toolkit.output.speech import BreakCommand, SpeechSequence


class FlowOutput(Protocol):
    def cancel_speech(self) -> None: ...
    def speak(self, items: Iterable[object]) -> None: ...
    def beep_failure(self) -> None: ...


class Access8GraphFlowOutput:
    def __init__(
        self,
        speech: SpeechOutputPort,
        tone: ToneOutput | None = None,
    ) -> None:
        self._speech = speech
        self._tone = tone

    def cancel_speech(self) -> None:
        self._speech.cancel()

    def speak(self, items: Iterable[object]) -> None:
        filtered = tuple(str(item) for item in items if item)
        if not filtered:
            return
        sequence_items: list[object] = []
        for index, item in enumerate(filtered):
            if index > 0:
                sequence_items.append(BreakCommand(time=1))
            sequence_items.append(item)
        self._speech.speak(SpeechSequence(items=tuple(sequence_items)))

    def beep_failure(self) -> None:
        tone = self._tone
        if tone is None:
            return
        beep = getattr(tone, "beep", None)
        if callable(beep):
            beep(100, 100)
