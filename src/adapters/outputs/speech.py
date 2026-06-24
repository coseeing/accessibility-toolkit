from interop.speech.speech_sequence import SpeechSequence
from adapters.outputs.interfaces import SpeechOutput
from application.output.speech.settings import SpeechNumericSetting


class NullSpeechOutput(SpeechOutput):
    def speak(self, sequence: SpeechSequence) -> None:
        return None

    def cancel(self) -> None:
        return None

    def pause(self, is_paused: bool) -> None:
        return None

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return ()

    def get_voice(self) -> str | None:
        return None

    def set_voice(self, voice_id: str) -> None:
        return None

    def get_rate(self) -> int | None:
        return None

    def set_rate(self, value: int) -> None:
        return None

    def get_pitch(self) -> int | None:
        return None

    def set_pitch(self, value: int) -> None:
        return None

    def get_volume(self) -> int | None:
        return None

    def set_volume(self, value: int) -> None:
        return None

    def get_supported_numeric_settings(self) -> tuple[SpeechNumericSetting, ...]:
        return ()
