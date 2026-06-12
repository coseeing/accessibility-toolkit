from apps.shared.speech_settings_controller import SpeechSettingsController


class FakeSpeech:
    def __init__(self):
        self.backend_id = "default"
        self.voice_id = "voice-1"
        self.rate = 50
        self.pitch = 40
        self.volume = 90
        self.backend_calls = []

    def get_backend_options(self):
        return (("default", "Default"), ("alt", "Alt"))

    def get_selected_backend(self):
        return self.backend_id

    def set_backend(self, backend_id):
        self.backend_calls.append(backend_id)
        self.backend_id = backend_id

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


def test_speech_settings_controller_proxies_backend_and_voice_settings():
    speech = FakeSpeech()
    controller = SpeechSettingsController(speech=speech)

    controller.set_backend("alt")
    controller.set_voice("voice-2")
    controller.set_rate(60)
    controller.set_pitch(55)
    controller.set_volume(80)

    assert controller.get_selected_backend() == "alt"
    assert controller.get_voice() == "voice-2"
    assert controller.get_rate() == 60
    assert controller.get_pitch() == 55
    assert controller.get_volume() == 80


def test_speech_settings_controller_calls_backend_changed_callback():
    seen = []
    speech = FakeSpeech()
    controller = SpeechSettingsController(
        speech=speech,
        on_backend_changed=seen.append,
    )

    controller.set_backend("alt")

    assert seen == ["alt"]
