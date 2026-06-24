from collections.abc import Callable

from application.output import SpeechServiceProtocol


class SpeechSettingsController:
    def __init__(
        self,
        *,
        speech: SpeechServiceProtocol,
        on_engine_changed: Callable[[str], None] | None = None,
        on_backend_changed: Callable[[str], None] | None = None,
        on_voice_changed: Callable[[str, str], None] | None = None,
        on_numeric_setting_changed: Callable[[str, str, int], None] | None = None,
    ) -> None:
        self._speech = speech
        self._on_engine_changed = on_engine_changed or on_backend_changed
        self._on_voice_changed = on_voice_changed
        self._on_numeric_setting_changed = on_numeric_setting_changed

    def get_engine_options(self) -> tuple[tuple[str, str], ...]:
        return self._speech.get_engine_options()

    def get_selected_engine(self) -> str:
        return self._speech.get_selected_engine()

    def set_engine(self, engine_id: str) -> None:
        self._speech.set_engine(engine_id)
        if self._on_engine_changed is not None:
            self._on_engine_changed(engine_id)

    def get_backend_options(self) -> tuple[tuple[str, str], ...]:
        return self.get_engine_options()

    def get_selected_backend(self) -> str:
        return self.get_selected_engine()

    def set_backend(self, backend_id: str) -> None:
        self.set_engine(backend_id)

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return self._speech.list_voices()

    def get_voice(self) -> str | None:
        return self._speech.get_voice()

    def set_voice(self, voice_id: str) -> None:
        self._speech.set_voice(voice_id)
        if self._on_voice_changed is not None:
            self._on_voice_changed(self.get_selected_engine(), voice_id)

    def get_rate(self) -> int | None:
        return self._speech.get_rate()

    def set_rate(self, value: int) -> None:
        self._speech.set_rate(value)
        if self._on_numeric_setting_changed is not None:
            self._on_numeric_setting_changed(self.get_selected_engine(), "rate", value)

    def get_pitch(self) -> int | None:
        return self._speech.get_pitch()

    def set_pitch(self, value: int) -> None:
        self._speech.set_pitch(value)
        if self._on_numeric_setting_changed is not None:
            self._on_numeric_setting_changed(self.get_selected_engine(), "pitch", value)

    def get_volume(self) -> int | None:
        return self._speech.get_volume()

    def set_volume(self, value: int) -> None:
        self._speech.set_volume(value)
        if self._on_numeric_setting_changed is not None:
            self._on_numeric_setting_changed(self.get_selected_engine(), "volume", value)

    def get_supported_numeric_settings(self):
        return self._speech.get_supported_numeric_settings()
