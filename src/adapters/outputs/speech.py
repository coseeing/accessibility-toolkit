from typing import Protocol

from remote_core.models.speech import NormalizedSpeech


class SpeechOutput(Protocol):
    def speak(self, speech: NormalizedSpeech) -> None: ...

    def cancel(self) -> None: ...

    def pause(self, is_paused: bool) -> None: ...


class NullSpeechOutput:
    def speak(self, speech: NormalizedSpeech) -> None:
        return None

    def cancel(self) -> None:
        return None

    def pause(self, is_paused: bool) -> None:
        return None
