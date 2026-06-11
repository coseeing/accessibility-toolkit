from application.state import ConnectionState, ControlState, RuntimeState
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


class FakeRunningCapture:
    def __init__(self):
        self.running = False
        self.started = 0
        self.stopped = 0

    def start(self):
        self.started += 1
        self.running = True

    def stop(self):
        self.stopped += 1
        self.running = False


class FakeRunningHotkey(FakeRunningCapture):
    pass


def test_control_mode_use_case_start_control_starts_capture_and_stops_hotkey():
    from apps.nvda_remote.use_cases.control_mode import NvdaRemoteControlModeUseCase

    state = RuntimeState(
        connection_state=ConnectionState.CONNECTED,
        control_state=ControlState.SUSPENDED,
    )
    input_capture = FakeRunningCapture()
    hotkey_capture = FakeRunningHotkey()
    hotkey_capture.running = True

    use_case = NvdaRemoteControlModeUseCase(
        state=state,
        input_capture=input_capture,
        hotkey_capture=hotkey_capture,
        notify_error=lambda _message: None,
        notify_status=lambda _status: None,
    )

    use_case.start_control()

    assert state.control_state == ControlState.CONTROLLING
    assert input_capture.started == 1
    assert hotkey_capture.stopped == 1
