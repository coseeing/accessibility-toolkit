from application.config import SpeechEngineConfigStore
from apps.shared.speech_runtime_settings import SpeechRuntimeSettingsCoordinator


class FakeSpeech:
    def __init__(self) -> None:
        self.selected_engine = "engine-a"
        self.voice = None
        self.rate = None
        self.pitch = None
        self.volume = None
        self.voices = (("voice-a", "Voice A"),)
        self.supported_settings = []

    def get_selected_engine(self) -> str:
        return self.selected_engine

    def list_voices(self):
        return self.voices

    def set_voice(self, voice_id: str) -> None:
        self.voice = voice_id

    def get_supported_numeric_settings(self):
        return self.supported_settings

    def set_rate(self, value: int) -> None:
        self.rate = value

    def set_pitch(self, value: int) -> None:
        self.pitch = value

    def set_volume(self, value: int) -> None:
        self.volume = value


class FakeSetting:
    def __init__(self, setting_id: str) -> None:
        self.id = setting_id


def test_coordinator_applies_saved_voice_and_supported_numeric_settings(tmp_path):
    store = SpeechEngineConfigStore(tmp_path / "speech.json")
    store.save_voice("engine-a", "voice-a")
    store.save_numeric_setting("engine-a", "rate", 70)
    store.save_numeric_setting("engine-a", "pitch", 20)
    store.save_numeric_setting("engine-a", "volume", 90)
    speech = FakeSpeech()
    speech.supported_settings = [FakeSetting("rate"), FakeSetting("volume")]
    coordinator = SpeechRuntimeSettingsCoordinator(config_store=store)

    coordinator.apply_saved_settings(speech=speech, engine_id="engine-a")

    assert speech.voice == "voice-a"
    assert speech.rate == 70
    assert speech.pitch is None
    assert speech.volume == 90


def test_coordinator_builds_engine_change_callback_that_persists_and_reapplies(tmp_path):
    store = SpeechEngineConfigStore(tmp_path / "speech.json")
    store.save_voice("engine-b", "voice-b")
    speech = FakeSpeech()
    speech.voices = (("voice-b", "Voice B"),)
    coordinator = SpeechRuntimeSettingsCoordinator(config_store=store)

    on_engine_changed = coordinator.build_engine_change_callback(speech=speech)
    on_engine_changed("engine-b")

    assert store.load_engine_id(default_engine_id="fallback") == "engine-b"
    assert speech.voice == "voice-b"
