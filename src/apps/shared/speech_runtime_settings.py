from __future__ import annotations

from application.output.speech import SpeechService
from application.output.speech.settings_store import SpeechSettingsStore


class SpeechRuntimeSettingsCoordinator:
    def __init__(self, *, config_store: SpeechSettingsStore) -> None:
        self._config_store = config_store

    def selected_engine_id(self, *, default_engine_id: str) -> str:
        return self._config_store.load_engine_id(default_engine_id=default_engine_id)

    def apply_saved_settings(self, *, speech: SpeechService, engine_id: str) -> None:
        voice_id = self._config_store.load_voice(engine_id)
        available_voice_ids = {voice for voice, _label in speech.list_voices()}
        if voice_id is not None and voice_id in available_voice_ids:
            speech.set_voice(voice_id)
        supported = {setting.id for setting in speech.get_supported_numeric_settings()}
        for setting_id, setter in (
            ("rate", speech.set_rate),
            ("pitch", speech.set_pitch),
            ("volume", speech.set_volume),
        ):
            value = self._config_store.load_numeric_setting(engine_id, setting_id)
            if value is not None and setting_id in supported:
                setter(value)

    def build_engine_change_callback(self, *, speech: SpeechService):
        def _on_engine_changed(engine_id: str) -> None:
            self._config_store.save_engine_id(engine_id)
            self.apply_saved_settings(speech=speech, engine_id=engine_id)

        return _on_engine_changed
