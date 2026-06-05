from remote_core.models.speech_sequence import SpeechSequence
from adapters.outputs.interfaces import SpeechOutput


class NullSpeechOutput(SpeechOutput):
    def speak(self, sequence: SpeechSequence) -> None:
        return None

    def cancel(self) -> None:
        return None

    def pause(self, is_paused: bool) -> None:
        return None

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return ()
