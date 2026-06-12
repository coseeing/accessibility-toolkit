from adapters.inputs.base import KeyEventDecision
from application.state import ConnectionState, ControlState, RuntimeState
from interop.key import HID, KeyEvent

from apps.nvda_remote.use_cases.state_transition_hotkeys import (
    NvdaRemoteHotkeyAction,
    NvdaRemoteStateTransitionHotkeyUseCase,
)


def test_nvda_hotkey_use_case_maps_f11_keydown_to_toggle_control():
    use_case = NvdaRemoteStateTransitionHotkeyUseCase(
        mapping={HID.F11: NvdaRemoteHotkeyAction.TOGGLE_CONTROL}
    )

    action = use_case.match(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F11, pressed=True))

    assert action == NvdaRemoteHotkeyAction.TOGGLE_CONTROL


def test_nvda_hotkey_use_case_ignores_f11_keyup():
    use_case = NvdaRemoteStateTransitionHotkeyUseCase(
        mapping={HID.F11: NvdaRemoteHotkeyAction.TOGGLE_CONTROL}
    )

    action = use_case.match(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F11, pressed=False))

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
        control_state=ControlState.CONNECTED,
    )
    notifications: list[dict[str, str]] = []

    use_case = NvdaRemoteControlModeUseCase(
        state=state,
        notify_error=lambda _message: None,
        notify_status=notifications.append,
    )

    use_case.start_control()

    assert state.control_state == ControlState.CONTROLLING
    assert notifications == [{"kind": "control", "state": ControlState.CONTROLLING.value}]


def test_control_mode_use_case_stop_control_stops_capture_and_restarts_hotkey():
    from apps.nvda_remote.use_cases.control_mode import NvdaRemoteControlModeUseCase

    state = RuntimeState(
        connection_state=ConnectionState.CONNECTED,
        control_state=ControlState.CONTROLLING,
    )
    notifications: list[dict[str, str]] = []

    use_case = NvdaRemoteControlModeUseCase(
        state=state,
        notify_error=lambda _message: None,
        notify_status=notifications.append,
    )

    use_case.stop_control()

    assert state.control_state == ControlState.CONNECTED
    assert notifications == [{"kind": "control", "state": ControlState.CONNECTED.value}]


def test_input_forwarding_use_case_sends_remote_key_when_controlling():
    from apps.nvda_remote.use_cases.input_forwarding import NvdaRemoteInputForwardingUseCase

    sent = []
    use_case = NvdaRemoteInputForwardingUseCase(
        is_connected=lambda: True,
        is_controlling=lambda: True,
        send_key=lambda payload: sent.append(payload),
        on_local_stop=lambda: None,
    )
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)

    decision = use_case.handle(event)

    assert decision == KeyEventDecision.SUPPRESS
    assert sent == [{"vk_code": 65, "scan_code": 30, "extended": False, "pressed": True}]


def test_input_forwarding_passes_through_unsupported_usage():
    from apps.nvda_remote.use_cases.input_forwarding import NvdaRemoteInputForwardingUseCase

    sent = []
    use_case = NvdaRemoteInputForwardingUseCase(
        is_connected=lambda: True,
        is_controlling=lambda: True,
        send_key=lambda payload: sent.append(payload),
        on_local_stop=lambda: None,
    )
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=0xFF, pressed=True)

    decision = use_case.handle(event)

    assert decision == KeyEventDecision.PASS_THROUGH
    assert sent == []
