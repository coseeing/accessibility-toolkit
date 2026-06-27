from apps.shared.speech_settings_facade import SpeechSettingsFacade


class SpeechSettingsController(SpeechSettingsFacade):
    def get_engine_options(self) -> tuple[tuple[str, str], ...]:
        return self.get_speech_engine_options()

    def get_selected_engine(self) -> str:
        return self.get_selected_speech_engine()

    def set_engine(self, engine_id: str) -> None:
        self.set_speech_engine(engine_id)

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return self.get_available_voices()

    def get_voice(self) -> str | None:
        return self.get_selected_voice()

    def set_voice(self, voice_id: str) -> None:
        self.set_selected_voice(voice_id)
