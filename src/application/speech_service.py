from adapters.outputs.interfaces import SpeechOutput
from application.speech_backends import SpeechBackendManager, SpeechBackendOption
from interop.speech.speech_sequence import SpeechSequence


class SpeechService:
    def __init__(
        self,
        *,
        backend_options: tuple[SpeechBackendOption, ...],
        selected_backend_id: str,
    ) -> None:
        self._backend_manager = SpeechBackendManager(
            backend_options=backend_options,
            selected_backend_id=selected_backend_id,
        )

    @classmethod
    def single_backend(cls, output: SpeechOutput) -> "SpeechService":
        return cls(
            backend_options=(
                SpeechBackendOption(
                    backend_id="default",
                    label="Default",
                    factory=lambda: output,
                ),
            ),
            selected_backend_id="default",
        )

    def speak(self, sequence: SpeechSequence) -> None:
        self._backend_manager.current_output.speak(sequence)

    def cancel(self) -> None:
        self._backend_manager.current_output.cancel()

    def pause(self, is_paused: bool) -> None:
        self._backend_manager.current_output.pause(is_paused)

    def get_backend_options(self) -> tuple[tuple[str, str], ...]:
        return self._backend_manager.backend_choices()

    def get_selected_backend(self) -> str:
        return self._backend_manager.selected_backend_id

    def set_backend(self, backend_id: str) -> None:
        self._backend_manager.set_backend(backend_id)

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return self._backend_manager.current_output.list_voices()

    def get_voice(self) -> str | None:
        return self._backend_manager.current_output.get_voice()

    def set_voice(self, voice_id: str) -> None:
        self._backend_manager.current_output.set_voice(voice_id)

    def get_rate(self) -> int | None:
        return self._backend_manager.current_output.get_rate()

    def set_rate(self, value: int) -> None:
        self._backend_manager.current_output.set_rate(value)

    def get_pitch(self) -> int | None:
        return self._backend_manager.current_output.get_pitch()

    def set_pitch(self, value: int) -> None:
        self._backend_manager.current_output.set_pitch(value)

    def get_volume(self) -> int | None:
        return self._backend_manager.current_output.get_volume()

    def set_volume(self, value: int) -> None:
        self._backend_manager.current_output.set_volume(value)
