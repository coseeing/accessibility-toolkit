from interop.key.key_event import KeyEvent

from apps.nvda_remote.use_cases.state_transition_hotkeys import (
    NvdaRemoteHotkeyAction,
    NvdaRemoteStateTransitionHotkeyUseCase,
)


def test_nvda_hotkey_use_case_maps_f11_keydown_to_toggle_control():
    use_case = NvdaRemoteStateTransitionHotkeyUseCase(
        mapping={0x7A: NvdaRemoteHotkeyAction.TOGGLE_CONTROL}
    )

    action = use_case.match(KeyEvent(vk=0x7A, scan=87, extended=False, pressed=True))

    assert action == NvdaRemoteHotkeyAction.TOGGLE_CONTROL


def test_nvda_hotkey_use_case_ignores_f11_keyup():
    use_case = NvdaRemoteStateTransitionHotkeyUseCase(
        mapping={0x7A: NvdaRemoteHotkeyAction.TOGGLE_CONTROL}
    )

    action = use_case.match(KeyEvent(vk=0x7A, scan=87, extended=False, pressed=False))

    assert action is None


class FakeSpeech:
    def __init__(self):
        self.backend_id = "nvda_controller"
        self.voice_id = None
        self.rate = None
        self.pitch = None
        self.volume = None

    def get_backend_options(self):
        return (("nvda_controller", "NVDA Controller"),)

    def get_selected_backend(self):
        return self.backend_id

    def set_backend(self, backend_id):
        self.backend_id = backend_id

    def list_voices(self):
        return ()

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


def test_nvda_speech_settings_use_case_proxies_backend_and_voice_controls():
    from apps.nvda_remote.use_cases.speech_settings import NvdaRemoteSpeechSettingsUseCase

    speech = FakeSpeech()
    saved = []
    use_case = NvdaRemoteSpeechSettingsUseCase(
        speech=speech,
        on_backend_changed=saved.append,
    )

    use_case.set_backend("pyttsx3")
    use_case.set_voice("voice-2")
    use_case.set_rate(120)

    assert speech.get_selected_backend() == "pyttsx3"
    assert speech.get_voice() == "voice-2"
    assert speech.get_rate() == 120
    assert saved == ["pyttsx3"]
