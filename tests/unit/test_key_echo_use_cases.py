from interop.key.key_event import KeyEvent

from apps.key_echo.use_cases.state_transition_hotkeys import (
    KeyEchoHotkeyAction,
    KeyEchoStateTransitionHotkeyUseCase,
)


def test_key_echo_hotkey_use_case_maps_enter_to_start_echo():
    use_case = KeyEchoStateTransitionHotkeyUseCase(
        mapping={
            0x0D: KeyEchoHotkeyAction.START_ECHO,
            0x1B: KeyEchoHotkeyAction.STOP_ECHO,
        }
    )

    action = use_case.match(KeyEvent(vk=0x0D, scan=28, extended=False, pressed=True))

    assert action == KeyEchoHotkeyAction.START_ECHO


def test_key_echo_hotkey_use_case_maps_escape_to_stop_echo():
    use_case = KeyEchoStateTransitionHotkeyUseCase(
        mapping={
            0x0D: KeyEchoHotkeyAction.START_ECHO,
            0x1B: KeyEchoHotkeyAction.STOP_ECHO,
        }
    )

    action = use_case.match(KeyEvent(vk=0x1B, scan=1, extended=False, pressed=True))

    assert action == KeyEchoHotkeyAction.STOP_ECHO


def test_key_echo_hotkey_use_case_ignores_keyup():
    use_case = KeyEchoStateTransitionHotkeyUseCase(
        mapping={
            0x0D: KeyEchoHotkeyAction.START_ECHO,
            0x1B: KeyEchoHotkeyAction.STOP_ECHO,
        }
    )

    action = use_case.match(KeyEvent(vk=0x1B, scan=1, extended=False, pressed=False))

    assert action is None


class FakeSpeech:
    def __init__(self):
        self.backend_id = "default"
        self.voice_id = None
        self.rate = None
        self.pitch = None
        self.volume = None

    def get_backend_options(self):
        return (("default", "Default"),)

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


def test_key_echo_speech_settings_use_case_proxies_backend_and_voice_controls():
    from apps.key_echo.use_cases.speech_settings import KeyEchoSpeechSettingsUseCase

    speech = FakeSpeech()
    use_case = KeyEchoSpeechSettingsUseCase(speech=speech)

    use_case.set_backend("pyttsx3")
    use_case.set_voice("voice-2")
    use_case.set_rate(120)

    assert speech.get_selected_backend() == "pyttsx3"
    assert speech.get_voice() == "voice-2"
    assert speech.get_rate() == 120
