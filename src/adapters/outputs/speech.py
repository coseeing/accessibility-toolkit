from typing import Protocol

from remote_core.models.speech_sequence import SpeechSequence


class SpeechOutput(Protocol):
    def speak(self, sequence: SpeechSequence) -> None: ...

    def cancel(self) -> None: ...

    def pause(self, is_paused: bool) -> None: ...

    def list_voices(self) -> tuple[tuple[str, str], ...]: ...

    def get_voice(self) -> str | None: ...

    def set_voice(self, voice_id: str) -> None: ...

    def get_rate(self) -> int | None: ...

    def set_rate(self, value: int) -> None: ...

    def get_pitch(self) -> int | None: ...

    def set_pitch(self, value: int) -> None: ...

    def get_volume(self) -> int | None: ...

    def set_volume(self, value: int) -> None: ...


class NullSpeechOutput:
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
