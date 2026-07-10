from apps.nvda_remote.state import ConnectionState, ControlState, RuntimeState
from apps.nvda_remote.events import RemoteConnectionChanged, RemoteControlChanged, RemoteMessageReceived
from accessibility_toolkit.input import HID, KeyEvent

from accessibility_toolkit.input.capture import KeyEventDecision
from accessibility_toolkit.input.events import CapturedKeyEvent


class FakeSpeech:
    def __init__(self):
        self.engine_id = "nvda_controller"
        self.voice_id = None
        self.rate = None
        self.pitch = None
        self.volume = None

    def get_engine_options(self):
        return (("nvda_controller", "NVDA Controller"),)

    def get_selected_engine(self):
        return self.engine_id

    def set_engine(self, engine_id):
        self.engine_id = engine_id

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


def test_nvda_speech_settings_use_case_proxies_engine_and_voice_controls():
    from accessibility_toolkit.output.speech import SpeechSettingsFacade

    speech = FakeSpeech()
    saved = []
    use_case = SpeechSettingsFacade(
        speech=speech,
        on_engine_changed=saved.append,
    )

    use_case.set_speech_engine("pyttsx3")
    use_case.set_selected_voice("voice-2")
    use_case.set_rate(120)

    assert speech.get_selected_engine() == "pyttsx3"
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
    notifications: list[RemoteControlChanged] = []

    use_case = NvdaRemoteControlModeUseCase(
        state=state,
        notify_error=lambda _message: None,
        notify_status=notifications.append,
    )

    use_case.start_control()

    assert state.control_state == ControlState.CONTROLLING
    assert notifications == [RemoteControlChanged(ControlState.CONTROLLING.value)]


def test_control_mode_use_case_stop_control_stops_capture_and_restarts_hotkey():
    from apps.nvda_remote.use_cases.control_mode import NvdaRemoteControlModeUseCase

    state = RuntimeState(
        connection_state=ConnectionState.CONNECTED,
        control_state=ControlState.CONTROLLING,
    )
    notifications: list[RemoteControlChanged] = []

    use_case = NvdaRemoteControlModeUseCase(
        state=state,
        notify_error=lambda _message: None,
        notify_status=notifications.append,
    )

    use_case.stop_control()

    assert state.control_state == ControlState.CONNECTED
    assert notifications == [RemoteControlChanged(ControlState.CONNECTED.value)]


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

    decision = use_case.handle(CapturedKeyEvent(key_event=event, native_context=None))

    assert decision == KeyEventDecision.SUPPRESS
    assert sent == [{"vk_code": 65, "scan_code": 30, "extended": False, "pressed": True}]


def test_input_forwarding_suppresses_unsupported_usage():
    from apps.nvda_remote.use_cases.input_forwarding import NvdaRemoteInputForwardingUseCase

    sent = []
    use_case = NvdaRemoteInputForwardingUseCase(
        is_connected=lambda: True,
        is_controlling=lambda: True,
        send_key=lambda payload: sent.append(payload),
        on_local_stop=lambda: None,
    )
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=0xFF, pressed=True)

    decision = use_case.handle(CapturedKeyEvent(key_event=event, native_context=None))

    assert decision == KeyEventDecision.SUPPRESS
    assert sent == []


def test_forwarding_suppresses_unsupported_non_us_backslash_in_control_mode(caplog):
    import logging
    from apps.nvda_remote.use_cases.input_forwarding import NvdaRemoteInputForwardingUseCase

    logging.getLogger("apps.nvda_remote.use_cases.input_forwarding").setLevel(logging.DEBUG)

    sent = []
    use_case = NvdaRemoteInputForwardingUseCase(
        is_connected=lambda: True,
        is_controlling=lambda: True,
        send_key=lambda payload: sent.append(payload),
        on_local_stop=lambda: None,
    )

    decision = use_case.handle(
        CapturedKeyEvent(
            key_event=KeyEvent(
                usage_page=HID.KEYBOARD_PAGE,
                usage=HID.NON_US_BACKSLASH,
                pressed=True,
            ),
            native_context=None,
        )
    )

    assert decision == KeyEventDecision.SUPPRESS
    assert sent == []
    assert "0x64" in caplog.text
    assert "unsupported usage" in caplog.text


def test_forwarding_suppresses_unsupported_jis_key_in_control_mode(caplog):
    import logging
    from apps.nvda_remote.use_cases.input_forwarding import NvdaRemoteInputForwardingUseCase

    logging.getLogger("apps.nvda_remote.use_cases.input_forwarding").setLevel(logging.DEBUG)

    sent = []
    use_case = NvdaRemoteInputForwardingUseCase(
        is_connected=lambda: True,
        is_controlling=lambda: True,
        send_key=lambda payload: sent.append(payload),
        on_local_stop=lambda: None,
    )

    decision = use_case.handle(
        CapturedKeyEvent(
            key_event=KeyEvent(
                usage_page=HID.KEYBOARD_PAGE,
                usage=HID.INTERNATIONAL3,
                pressed=True,
            ),
            native_context=None,
        )
    )

    assert decision == KeyEventDecision.SUPPRESS
    assert sent == []
    assert "0x89" in caplog.text
    assert "unsupported usage" in caplog.text


def test_remote_connection_use_case_sets_connected_state_and_requests_hotkey_start():
    state = RuntimeState()
    effects = []
    from apps.nvda_remote.use_cases.connection import RemoteConnectionUseCase

    use_case = RemoteConnectionUseCase(
        state=state,
        exit_active=lambda: effects.append("exit_active"),
        ensure_hotkey_started=lambda: effects.append("ensure_hotkey_started"),
        stop_capture=lambda: effects.append("stop_capture"),
        stop_hotkey=lambda: effects.append("stop_hotkey"),
        notify=lambda event: effects.append(event),
    )

    use_case.handle_connected()

    assert state.connection_state == ConnectionState.CONNECTED
    assert state.control_state == ControlState.CONNECTED
    assert effects == [
        "exit_active",
        "ensure_hotkey_started",
        RemoteConnectionChanged("connected"),
    ]


def test_remote_protocol_event_handler_maps_remote_peer_messages():
    from apps.nvda_remote.use_cases.protocol_events import RemoteProtocolEventHandler
    from accessibility_toolkit.remote.events import RemotePeerMessageReceived, RemoteSessionConnected

    delivered = []
    handler = RemoteProtocolEventHandler(
        on_connected=lambda: delivered.append("connected"),
        on_disconnected=lambda: delivered.append("disconnected"),
        notify_remote_message=lambda event: delivered.append(event),
    )

    handler.handle(RemoteSessionConnected())
    handler.handle(
        RemotePeerMessageReceived(
            message_type="motd",
            payload={"type": "motd", "message": "hello"},
        )
    )

    assert delivered == [
        "connected",
        RemoteMessageReceived("motd", {"type": "motd", "message": "hello"}),
    ]
