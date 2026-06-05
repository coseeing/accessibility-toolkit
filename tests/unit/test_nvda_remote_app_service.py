from adapters.inputs.base import KeyEventDecision
from remote_core.models.keys import KeyEvent
from remote_core.protocol import RemoteMessageType

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


class FakeSpeechService:
    def __init__(self):
        self.spoken = []
        self.cancelled = 0
        self.paused = []

    def speak(self, sequence):
        self.spoken.append(sequence)

    def cancel(self):
        self.cancelled += 1

    def pause(self, is_paused):
        self.paused.append(is_paused)


def build_service():
    transport = FakeTransport()
    capture = FakeCapture()
    hotkey = FakeHotkey()
    service = NvdaRemoteAppService(
        transport=transport,
        input_capture=capture,
        hotkey_capture=hotkey,
        clipboard=FakeClipboard(),
        speech=FakeSpeechService(),
        main_thread_dispatch=lambda callback: callback(),
    )
    return service, transport, capture, hotkey


def test_nvda_remote_service_forwards_keys_when_controlling():
    service, transport, capture, hotkey = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.start_control()
    event = KeyEvent(vk=65, scan=30, extended=False, pressed=True)

    decision = service.handle_key_event(event)

    assert decision == KeyEventDecision.FORWARD_AND_SUPPRESS
    assert transport.sent == [(RemoteMessageType.KEY, event.to_remote_payload())]
    assert capture.started == 1
    assert capture.running is True
    assert hotkey.stopped == 0


def test_nvda_remote_service_passes_through_keys_before_control():
    service, transport, _capture, _hotkey = build_service()
    service.state.connection_state = service.state.connection_state.CONNECTED

    decision = service.handle_key_event(
        KeyEvent(vk=65, scan=30, extended=False, pressed=True)
    )

    assert decision == KeyEventDecision.PASS_THROUGH
    assert transport.sent == []


def test_nvda_remote_service_uses_f11_as_local_stop():
    service, transport, capture, hotkey = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.start_control()

    keydown_decision = service.handle_key_event(
        KeyEvent(vk=0x7A, scan=87, extended=False, pressed=True)
    )
    keyup_decision = service.handle_key_event(
        KeyEvent(vk=0x7A, scan=87, extended=False, pressed=False)
    )

    assert keydown_decision == KeyEventDecision.LOCAL_ONLY_SUPPRESS
    assert keyup_decision == KeyEventDecision.LOCAL_ONLY_SUPPRESS
    assert service.state.control_state == service.state.control_state.SUSPENDED
    assert transport.sent == []
    assert capture.stopped == 1
    assert hotkey.started == 1
    assert hotkey.running is True


def test_nvda_remote_service_routes_remote_speech_commands_into_speech_facade():
    service, transport, _capture, _hotkey = build_service()
    service.bind()

    transport.message_handler({"type": RemoteMessageType.SPEAK.value, "sequence": ["hi"]})
    transport.message_handler({"type": RemoteMessageType.CANCEL.value})
    transport.message_handler({"type": RemoteMessageType.PAUSE_SPEECH.value, "switch": True})

    assert [speech.items for speech in service.speech.spoken] == [("hi",)]
    assert service.speech.cancelled == 1
    assert service.speech.paused == [True]


def test_nvda_remote_service_registers_transport_message_handler():
    service, transport, capture, hotkey = build_service()

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


def test_nvda_remote_service_does_not_swallow_f11_when_not_controlling():
    service, transport, _capture, _hotkey = build_service()
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
