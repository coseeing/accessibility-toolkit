from adapters.inputs.captured_event import CapturedKeyEvent
from adapters.windows.native_key_context import WindowsNativeKeyContext
from application.events import ErrorRaised, ModeChanged, SpeechBackendChanged
from application.input.results import AppKeyEventResult, KeyboardPipelineResult
from application.output import Capabilities
from interop.key import HID, KeyEvent
from interop.protocol.messages import RemoteMessageType
from interop.protocol.routing.message_router import MessageRouter

from apps.nvda_remote.events import (
    RemoteConnectionChanged,
    RemoteControlChanged,
    RemoteMessageReceived,
    RemoteTransportDisconnected,
)
from apps.nvda_remote.service import NvdaRemoteAppService


class FakeTransport:
    def __init__(self):
        self.sent = []
        self.message_handler = None
        self.reader_started = 0
        self.reader_stopped = 0

    def send(self, message_type, **payload):
        self.sent.append((message_type, payload))

    def set_message_handler(self, handler):
        self.message_handler = handler

    def start_reader(self):
        self.reader_started += 1

    def stop_reader(self):
        self.reader_stopped += 1


class FakeCapture:
    def __init__(self):
        self.running = False
        self.listener = None
        self.started = 0
        self.stopped = 0

    def set_listener(self, listener):
        self.listener = listener

    def start(self):
        self.started += 1
        self.running = True

    def stop(self):
        self.stopped += 1
        self.running = False


class FakeHotkey:
    def __init__(self):
        self.handler = None
        self.running = False
        self.started = 0
        self.stopped = 0

    def set_handler(self, handler):
        self.handler = handler

    def start(self):
        self.started += 1
        self.running = True

    def stop(self):
        self.stopped += 1
        self.running = False


class FakeClipboard:
    def __init__(self):
        self.text = ""

    def set_text(self, text):
        self.text = text

    def get_text(self):
        return "clip"


class FakeToneService:
    def __init__(self) -> None:
        self.calls = []

    def beep(self, hz: float, length: int, left: int = 50, right: int = 50) -> None:
        self.calls.append((hz, length, left, right))


class FakeSpeechService:
    def __init__(self):
        self.spoken = []
        self.cancelled = 0
        self.paused = []
        self.backend_options = (("nvda_controller", "NVDA Controller"),)
        self.selected_backend = "nvda_controller"
        self.backend_calls = []

    def speak(self, sequence):
        self.spoken.append(sequence)

    def cancel(self):
        self.cancelled += 1

    def pause(self, is_paused):
        self.paused.append(is_paused)

    def get_backend_options(self):
        return self.backend_options

    def get_selected_backend(self):
        return self.selected_backend

    def set_backend(self, backend_id):
        self.backend_calls.append(backend_id)
        self.selected_backend = backend_id

    def list_voices(self):
        return ()

    def get_voice(self):
        return None

    def set_voice(self, _voice_id):
        return None

    def get_rate(self):
        return None

    def set_rate(self, _value):
        return None

    def get_pitch(self):
        return None

    def set_pitch(self, _value):
        return None

    def get_volume(self):
        return None

    def set_volume(self, _value):
        return None


def build_service(*, dispatch=None, use_windows_native_key_payload=False):
    transport = FakeTransport()
    capture = FakeCapture()
    hotkey = FakeHotkey()
    dispatch_calls = []

    def dispatch_wrapper(callback):
        dispatch_calls.append(callback)
        if dispatch is not None:
            return dispatch(callback)
        return callback()

    tone = FakeToneService()
    service = NvdaRemoteAppService(
        transport=transport,
        input_capture=capture,
        hotkey_capture=hotkey,
        clipboard=FakeClipboard(),
        capabilities=Capabilities(speech=FakeSpeechService(), tone=tone),
        main_thread_dispatch=dispatch_wrapper,
        use_windows_native_key_payload=use_windows_native_key_payload,
    )
    return service, transport, capture, hotkey, dispatch_calls


def test_nvda_remote_service_forwards_keys_when_controlling():
    service, transport, capture, hotkey, _dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.start_control()
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)

    decision = service.handle_key_event(CapturedKeyEvent(key_event=event, native_context=None))

    assert decision == KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
    assert transport.sent == [(RemoteMessageType.KEY, {"vk_code": 65, "scan_code": 30, "extended": False, "pressed": True})]


def test_nvda_remote_service_defaults_to_hid_payload_forwarding():
    service, transport, _capture, _hotkey, _dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.start_control()

    decision = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(
                usage_page=HID.KEYBOARD_PAGE,
                usage=HID.KEYPAD_5,
                pressed=True,
            ),
            native_context=WindowsNativeKeyContext(vk_code=0x09, scan_code=15, extended=False),
            num_lock_on=False,
        )
    )

    assert decision == KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
    assert transport.sent == [(RemoteMessageType.KEY, {"vk_code": 0x0C, "scan_code": 76, "extended": False, "pressed": True})]


def test_nvda_remote_service_can_forward_windows_native_payloads():
    service, transport, _capture, _hotkey, _dispatch_calls = build_service(
        use_windows_native_key_payload=True
    )
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.start_control()

    decision = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(
                usage_page=HID.KEYBOARD_PAGE,
                usage=HID.KEYPAD_5,
                pressed=True,
            ),
            native_context=WindowsNativeKeyContext(vk_code=0x09, scan_code=15, extended=False),
            num_lock_on=False,
        )
    )

    assert decision == KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
    assert transport.sent == [(RemoteMessageType.KEY, {"vk_code": 0x09, "scan_code": 15, "extended": False, "pressed": True})]


def test_nvda_remote_service_passes_num_lock_through_when_controlling_on_windows():
    service, transport, capture, hotkey, _dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.start_control()

    decision = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(
                usage_page=HID.KEYBOARD_PAGE,
                usage=HID.NUM_LOCK,
                pressed=True,
            ),
            native_context=WindowsNativeKeyContext(vk_code=0x90, scan_code=69, extended=True),
        )
    )

    assert decision == KeyboardPipelineResult(send_to_system=True, app_result=AppKeyEventResult.UNHANDLED)
    assert transport.sent == []


def test_nvda_remote_service_passes_through_keys_before_control():
    service, transport, _capture, _hotkey, _dispatch_calls = build_service()
    service.state.connection_state = service.state.connection_state.CONNECTED

    decision = service.handle_key_event(
        CapturedKeyEvent(key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True), native_context=None)
    )

    assert decision == KeyboardPipelineResult(send_to_system=True, app_result=AppKeyEventResult.UNHANDLED)
    assert transport.sent == []


def test_nvda_remote_service_uses_f11_as_local_stop():
    service, transport, capture, hotkey, _dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.start_control()

    keydown_decision = service.handle_key_event(
        CapturedKeyEvent(key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F11, pressed=True), native_context=None)
    )
    keyup_decision = service.handle_key_event(
        CapturedKeyEvent(key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F11, pressed=False), native_context=None)
    )

    assert keydown_decision == KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
    assert keyup_decision == KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
    assert service.state.control_state == service.state.control_state.CONNECTED
    assert transport.sent == []
    assert hotkey.started == 1
    assert hotkey.running is True


def test_nvda_remote_service_routes_remote_speech_commands_into_speech_facade():
    service, transport, _capture, _hotkey, _dispatch_calls = build_service()
    service.bind()

    transport.message_handler({"type": RemoteMessageType.SPEAK.value, "sequence": ["hi"]})
    transport.message_handler({"type": RemoteMessageType.CANCEL.value})
    transport.message_handler({"type": RemoteMessageType.PAUSE_SPEECH.value, "switch": True})

    assert [speech.items for speech in service._capabilities.speech.spoken] == [("hi",)]
    assert service._capabilities.speech.cancelled == 1
    assert service._capabilities.speech.paused == [True]


def test_nvda_remote_service_registers_transport_message_handler():
    service, transport, capture, hotkey, _dispatch_calls = build_service()

    assert transport.message_handler is None
    assert capture.listener is None
    assert hotkey.handler is None

    service.bind()

    assert transport.message_handler is not None
    assert capture.listener == service.handle_key_event
    assert hotkey.handler is not None
    transport.message_handler({"type": RemoteMessageType.CHANNEL_JOINED.value})

    assert service.state.connection_state == service.state.connection_state.CONNECTED
    assert hotkey.started == 1


def test_nvda_remote_service_does_not_swallow_unmapped_key_when_not_controlling():
    service, transport, _capture, _hotkey, _dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.state.control_state = service.state.control_state.CONNECTED

    keydown_decision = service.handle_key_event(
        CapturedKeyEvent(key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True), native_context=None)
    )
    keyup_decision = service.handle_key_event(
        CapturedKeyEvent(key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=False), native_context=None)
    )

    assert keydown_decision == KeyboardPipelineResult(send_to_system=True, app_result=AppKeyEventResult.UNHANDLED)
    assert keyup_decision == KeyboardPipelineResult(send_to_system=True, app_result=AppKeyEventResult.UNHANDLED)
    assert service.state.control_state == service.state.control_state.CONNECTED
    assert transport.sent == []


def test_nvda_remote_service_dispatches_status_updates_through_main_thread_callback():
    delivered = []

    def deferred_dispatch(callback):
        pending.append(callback)

    pending = []
    service, transport, _capture, hotkey, dispatch_calls = build_service(
        dispatch=deferred_dispatch
    )
    service.bind()
    service.set_status_listener(delivered.append)

    transport.message_handler({"type": RemoteMessageType.CHANNEL_JOINED.value})

    assert delivered == []
    assert len(dispatch_calls) == 1
    assert hotkey.started == 1

    pending.pop()()

    assert delivered == [RemoteConnectionChanged("connected")]


def test_nvda_remote_service_handles_transport_disconnected_message():
    service, transport, capture, hotkey, _dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.state.control_state = service.state.control_state.CONNECTED
    status_events = []
    service.set_status_listener(status_events.append)

    transport.message_handler(
        {"type": "transport_disconnected", "reason": "socket closed"}
    )

    assert service.state.connection_state == service.state.connection_state.IDLE
    assert service.state.control_state == service.state.control_state.IDLE
    assert status_events == [
        RemoteTransportDisconnected("socket closed"),
        RemoteConnectionChanged("idle"),
    ]


def test_nvda_remote_service_ignores_unknown_status_kinds_for_listener():
    service, _transport, _capture, _hotkey, _dispatch_calls = build_service()
    delivered = []
    service.set_status_listener(delivered.append)

    service._on_status({"kind": "invalid_message", "reason": "bad payload"})

    assert delivered == []


def test_nvda_remote_service_converts_remote_status_for_listener():
    service, transport, _capture, _hotkey, _dispatch_calls = build_service()
    service.bind()
    delivered = []
    service.set_status_listener(delivered.append)
    payload = {"type": RemoteMessageType.MOTD.value, "message": "hello"}

    transport.message_handler(payload)

    assert delivered == [RemoteMessageReceived("motd", payload)]


def test_nvda_remote_service_safely_converts_malformed_remote_status() -> None:
    service, _transport, _capture, _hotkey, _dispatch_calls = build_service()
    delivered = []
    service.set_status_listener(delivered.append)

    service._on_status({"kind": "remote", "type": 123, "payload": "bad"})

    assert delivered == [RemoteMessageReceived("123", {})]


def test_nvda_remote_service_start_and_stop_control_dispatch_control_events() -> None:
    pending = []

    def deferred_dispatch(callback):
        pending.append(callback)

    service, _transport, capture, _hotkey, dispatch_calls = build_service(
        dispatch=deferred_dispatch
    )
    service.state.connection_state = service.state.connection_state.CONNECTED
    delivered = []
    service.set_status_listener(delivered.append)

    service.start_control()

    assert service.state.control_state == service.state.control_state.CONTROLLING
    assert delivered == []
    assert len(dispatch_calls) == 2
    while pending:
        pending.pop(0)()
    assert delivered == [
        RemoteControlChanged("controlling"),
        ModeChanged("remote_control", active=True),
    ]

    service.stop_control()

    assert service.state.control_state == service.state.control_state.CONNECTED
    assert len(dispatch_calls) == 4
    while pending:
        pending.pop(0)()
    assert delivered == [
        RemoteControlChanged("controlling"),
        ModeChanged("remote_control", active=True),
        RemoteControlChanged("connected"),
        ModeChanged("remote_control", active=False),
    ]
    assert capture.running is False


def test_nvda_remote_service_stop_control_handles_hotkey_start_failure():
    service, transport, capture, hotkey, _dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    capture.running = True
    capture.started = 1
    service.start_control()
    status_events = []
    service.set_status_listener(status_events.append)

    failing = RuntimeError("hotkey busy")

    def _failing_start():
        hotkey.running = True
        raise failing

    hotkey.start = _failing_start

    decision = service.handle_key_event(
        CapturedKeyEvent(key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F11, pressed=True), native_context=None)
    )

    assert decision == KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
    assert service.state.control_state == service.state.control_state.CONTROLLING
    assert capture.running is True
    assert status_events == [
        ErrorRaised("hotkey busy"),
    ]


def test_nvda_remote_service_dispatches_speech_backend_notifications():
    delivered = []
    saved_backend_ids = []
    pending = []

    def deferred_dispatch(callback):
        pending.append(callback)

    service, _transport, _capture, _hotkey, dispatch_calls = build_service(
        dispatch=deferred_dispatch
    )
    service._on_speech_backend_changed = saved_backend_ids.append
    service.set_status_listener(delivered.append)

    service.set_speech_backend("pyttsx3")

    assert service._capabilities.speech.backend_calls == ["pyttsx3"]
    assert saved_backend_ids == ["pyttsx3"]
    assert delivered == []
    assert len(dispatch_calls) == 1

    pending.pop()()

    assert delivered == [SpeechBackendChanged("pyttsx3")]


def test_nvda_remote_service_f11_toggles_control_on_keydown_only():
    service, _transport, capture, hotkey, dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.state.control_state = service.state.control_state.CONNECTED
    hotkey.running = True

    hotkey.handler()

    assert len(dispatch_calls) == 1
    assert service.state.control_state == service.state.control_state.CONTROLLING
    assert hotkey.stopped == 1
    assert capture.started == 1


def test_nvda_remote_service_stop_control_is_noop_when_not_controlling():
    service, _transport, capture, hotkey, _dispatch_calls = build_service()

    assert service.state.connection_state == service.state.connection_state.IDLE
    assert service.state.control_state == service.state.control_state.IDLE
    assert capture.running is False
    assert hotkey.running is False

    service.stop_control()

    assert service.state.connection_state == service.state.connection_state.IDLE
    assert service.state.control_state == service.state.control_state.IDLE
    assert capture.started == 0
    assert capture.stopped == 0
    assert hotkey.started == 0
    assert hotkey.stopped == 0


def test_nvda_remote_service_returns_pipeline_result_while_controlling():
    service, transport, capture, hotkey, _dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.start_control()

    result = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True),
            native_context=None,
        )
    )

    assert result == KeyboardPipelineResult(
        send_to_system=False,
        app_result=AppKeyEventResult.HANDLED_STOP,
    )


def test_nvda_remote_service_routes_remote_tone_into_tone_output():
    service, transport, _capture, _hotkey, _dispatch_calls = build_service()
    service.bind()

    transport.message_handler(
        {
            "type": RemoteMessageType.TONE.value,
            "hz": 440,
            "length": 80,
            "left": 25,
            "right": 75,
        }
    )

    assert service._capabilities.tone.calls == [(440.0, 80, 25, 75)]


def test_nvda_remote_service_ignores_remote_tone_when_tone_output_is_missing():
    service, transport, _capture, _hotkey, _dispatch_calls = build_service()
    service._capabilities = Capabilities(speech=service._capabilities.speech)
    service.router = MessageRouter(
        on_speech=service._capabilities.speech.speak,
        on_cancel=service._capabilities.speech.cancel,
        on_pause=service._capabilities.speech.pause,
        on_clipboard=service.clipboard.set_text,
        on_tone=service._handle_tone,
        on_status=service._on_status,
    )
    service.bind()

    transport.message_handler(
        {
            "type": RemoteMessageType.TONE.value,
            "hz": 440,
            "length": 80,
            "left": 25,
            "right": 75,
        }
    )
