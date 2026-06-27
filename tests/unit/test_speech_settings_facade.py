from apps.shared.speech_settings_facade import SpeechSettingsFacade


class FakeSpeech:
    def __init__(self):
        self.engine_id = "default"
        self.voice_id = "voice-1"
        self.rate = 50
        self.pitch = 40
        self.volume = 90
        self.engine_calls = []

    def get_engine_options(self):
        return (("default", "Default"), ("alt", "Alt"))

    def get_selected_engine(self):
        return self.engine_id

    def set_engine(self, engine_id):
        self.engine_calls.append(engine_id)
        self.engine_id = engine_id

    def list_voices(self):
        return (("voice-1", "Voice 1"), ("voice-2", "Voice 2"))

    def get_voice(self):
        return self.voice_id

    def set_voice(self, voice_id):
        self.voice_id = voice_id

    def get_rate(self):
        return self.rate

    def set_rate(self, value):
        self.rate = value

    def get_pitch(self):
        return self.pitch

    def set_pitch(self, value):
        self.pitch = value

    def get_volume(self):
        return self.volume

    def set_volume(self, value):
        self.volume = value

    def get_supported_numeric_settings(self):
        return ("rate", "pitch", "volume")


def test_speech_settings_facade_proxies_engine_and_voice_settings():
    speech = FakeSpeech()
    facade = SpeechSettingsFacade(speech=speech)

    facade.set_speech_engine("alt")
    facade.set_selected_voice("voice-2")
    facade.set_rate(60)
    facade.set_pitch(55)
    facade.set_volume(80)

    assert facade.get_selected_speech_engine() == "alt"
    assert facade.get_selected_voice() == "voice-2"
    assert facade.get_rate() == 60
    assert facade.get_pitch() == 55
    assert facade.get_volume() == 80


def test_speech_settings_facade_calls_engine_changed_callback():
    seen = []
    speech = FakeSpeech()
    facade = SpeechSettingsFacade(
        speech=speech,
        on_engine_changed=seen.append,
    )

    facade.set_speech_engine("alt")

    assert seen == ["alt"]


def test_speech_settings_facade_calls_voice_and_numeric_callbacks():
    calls = []
    speech = FakeSpeech()
    facade = SpeechSettingsFacade(
        speech=speech,
        on_voice_changed=lambda engine_id, voice_id: calls.append(
            ("voice", engine_id, voice_id)
        ),
        on_numeric_setting_changed=lambda engine_id, setting_id, value: calls.append(
            ("numeric", engine_id, setting_id, value)
        ),
    )

    facade.set_speech_engine("alt")
    facade.set_selected_voice("voice-2")
    facade.set_rate(60)
    facade.set_pitch(55)
    facade.set_volume(80)

    assert calls == [
        ("voice", "alt", "voice-2"),
        ("numeric", "alt", "rate", 60),
        ("numeric", "alt", "pitch", 55),
        ("numeric", "alt", "volume", 80),
    ]


def test_speech_settings_facade_proxies_supported_numeric_settings():
    speech = FakeSpeech()
    facade = SpeechSettingsFacade(speech=speech)

    assert facade.get_supported_numeric_settings() == ("rate", "pitch", "volume")
