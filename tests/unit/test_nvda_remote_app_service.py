from adapters.inputs.base import KeyEventDecision
from interop.key.key_event import KeyEvent
from interop.protocol.messages import RemoteMessageType

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
        self.start_error = None

    def set_listener(self, listener):
        self.listener = listener

    def start(self):
        self.started += 1
        if self.start_error is not None:
            raise self.start_error
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
        self.start_error = None

    def set_handler(self, handler):
        self.handler = handler

    def start(self):
        self.started += 1
        if self.start_error is not None:
            raise self.start_error
        self.running = True

    def stop(self):
        self.stopped += 1
        self.running = False


class FakeClipboard:
    def __init__(self):
        self.text = ""
        self.supported = True

    def set_text(self, text):
        self.text = text

    def get_text(self):
        return "clip"


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


def build_service(*, dispatch=None):
    transport = FakeTransport()
    capture = FakeCapture()
    hotkey = FakeHotkey()
    dispatch_calls = []

    def dispatch_wrapper(callback):
        dispatch_calls.append(callback)
        if dispatch is not None:
            return dispatch(callback)
        return callback()

    service = NvdaRemoteAppService(
        transport=transport,
        input_capture=capture,
        hotkey_capture=hotkey,
        clipboard=FakeClipboard(),
        speech=FakeSpeechService(),
        main_thread_dispatch=dispatch_wrapper,
    )
    return service, transport, capture, hotkey, dispatch_calls


def test_nvda_remote_service_forwards_keys_when_controlling():
    service, transport, capture, hotkey, _dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.start_control()
    event = KeyEvent(vk=65, scan=30, extended=False, pressed=True)

    decision = service.handle_key_event(event)

    assert decision == KeyEventDecision.SUPPRESS
    assert transport.sent == [(RemoteMessageType.KEY, event.to_remote_payload())]
    assert capture.started == 1
    assert capture.running is True
    assert hotkey.stopped == 0


def test_nvda_remote_service_passes_through_keys_before_control():
    service, transport, _capture, _hotkey, _dispatch_calls = build_service()
    service.state.connection_state = service.state.connection_state.CONNECTED

    decision = service.handle_key_event(
        KeyEvent(vk=65, scan=30, extended=False, pressed=True)
    )

    assert decision == KeyEventDecision.PASS_THROUGH
    assert transport.sent == []


def test_nvda_remote_service_uses_f11_as_local_stop():
    service, transport, capture, hotkey, _dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.start_control()

    keydown_decision = service.handle_key_event(
        KeyEvent(vk=0x7A, scan=87, extended=False, pressed=True)
    )
    keyup_decision = service.handle_key_event(
        KeyEvent(vk=0x7A, scan=87, extended=False, pressed=False)
    )

    assert keydown_decision == KeyEventDecision.SUPPRESS
    assert keyup_decision == KeyEventDecision.SUPPRESS
    assert service.state.control_state == service.state.control_state.SUSPENDED
    assert transport.sent == []
    assert capture.stopped == 1
    assert hotkey.started == 1
    assert hotkey.running is True


def test_nvda_remote_service_start_control_reports_capture_start_errors():
    service, _transport, capture, hotkey, _dispatch_calls = build_service()
    service.bind()
    delivered = []
    service.set_status_listener(delivered.append)
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.state.control_state = service.state.control_state.CONNECTED
    hotkey.running = True
    capture.start_error = RuntimeError("capture unavailable")

    service.start_control()

    assert service.state.control_state == service.state.control_state.CONNECTED
    assert delivered[-1] == {"kind": "error", "message": "capture unavailable"}
    assert hotkey.started == 1
    assert hotkey.running is True


def test_nvda_remote_service_routes_remote_speech_commands_into_speech_facade():
    service, transport, _capture, _hotkey, _dispatch_calls = build_service()
    service.bind()

    transport.message_handler({"type": RemoteMessageType.SPEAK.value, "sequence": ["hi"]})
    transport.message_handler({"type": RemoteMessageType.CANCEL.value})
    transport.message_handler({"type": RemoteMessageType.PAUSE_SPEECH.value, "switch": True})

    assert [speech.items for speech in service.speech.spoken] == [("hi",)]
    assert service.speech.cancelled == 1
    assert service.speech.paused == [True]


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


def test_nvda_remote_service_reports_hotkey_start_errors_on_connect():
    service, transport, _capture, hotkey, _dispatch_calls = build_service()
    delivered = []
    service.set_status_listener(delivered.append)
    hotkey.start_error = RuntimeError("hotkey unavailable")
    service.bind()

    transport.message_handler({"type": RemoteMessageType.CHANNEL_JOINED.value})

    assert service.state.connection_state == service.state.connection_state.CONNECTED
    assert service.state.control_state == service.state.control_state.CONNECTED
    assert delivered[0] == {"kind": "error", "message": "hotkey unavailable"}
    assert delivered[-1] == {"kind": "connection", "state": "connected"}


def test_nvda_remote_service_reports_clipboard_availability():
    service, _transport, _capture, _hotkey, _dispatch_calls = build_service()

    assert service.is_clipboard_available() is True
    service.clipboard.supported = False
    assert service.is_clipboard_available() is False


def test_nvda_remote_service_does_not_swallow_f11_when_not_controlling():
    service, transport, _capture, _hotkey, _dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.state.control_state = service.state.control_state.SUSPENDED

    keydown_decision = service.handle_key_event(
        KeyEvent(vk=0x7A, scan=87, extended=False, pressed=True)
    )
    keyup_decision = service.handle_key_event(
        KeyEvent(vk=0x7A, scan=87, extended=False, pressed=False)
    )

    assert keydown_decision == KeyEventDecision.PASS_THROUGH
    assert keyup_decision == KeyEventDecision.PASS_THROUGH
    assert service.state.control_state == service.state.control_state.SUSPENDED
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

    assert delivered == [{"kind": "connection", "state": "connected"}]


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

    assert service.speech.backend_calls == ["pyttsx3"]
    assert saved_backend_ids == ["pyttsx3"]
    assert delivered == []
    assert len(dispatch_calls) == 1

    pending.pop()()

    assert delivered == [{"kind": "speech_backend", "backend_id": "pyttsx3"}]
