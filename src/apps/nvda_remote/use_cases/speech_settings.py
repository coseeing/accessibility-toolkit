from collections.abc import Callable

from application.output_service import SpeechOutputService


class NvdaRemoteSpeechSettingsUseCase:
    def __init__(
        self,
        *,
        speech: SpeechOutputService,
        on_backend_changed: Callable[[str], None] | None = None,
    ) -> None:
        self._speech = speech
        self._on_backend_changed = on_backend_changed

    def get_backend_options(self) -> tuple[tuple[str, str], ...]:
        return self._speech.get_backend_options()

    def get_selected_backend(self) -> str:
        return self._speech.get_selected_backend()

    def set_backend(self, backend_id: str) -> None:
        self._speech.set_backend(backend_id)
        if self._on_backend_changed is not None:
            self._on_backend_changed(backend_id)

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return self._speech.list_voices()

    def get_voice(self) -> str | None:
        return self._speech.get_voice()

    def set_voice(self, voice_id: str) -> None:
        self._speech.set_voice(voice_id)

    def get_rate(self) -> int | None:
        return self._speech.get_rate()

    def set_rate(self, value: int) -> None:
        self._speech.set_rate(value)

    def get_pitch(self) -> int | None:
        return self._speech.get_pitch()

    def set_pitch(self, value: int) -> None:
        self._speech.set_pitch(value)

    def get_volume(self) -> int | None:
        return self._speech.get_volume()

    def set_volume(self, value: int) -> None:
        self._speech.set_volume(value)
