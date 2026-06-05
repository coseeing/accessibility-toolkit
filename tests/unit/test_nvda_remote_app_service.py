from adapters.inputs.base import KeyEventDecision
from remote_core.models.keys import KeyEvent
from remote_core.protocol import RemoteMessageType

from apps.nvda_remote.service import NvdaRemoteAppService


class FakeTransport:
    def __init__(self):
        self.sent = []
        self.message_handler = None

    def send(self, message_type, **payload):
        self.sent.append((message_type, payload))

    def set_message_handler(self, handler):
        self.message_handler = handler


class FakeCapture:
    def __init__(self):
        self.running = False

    def set_listener(self, listener):
        self.listener = listener

    def start(self):
        self.running = True

    def stop(self):
        self.running = False


class FakeHotkey:
    def set_handler(self, handler):
        self.handler = handler

    def start(self):
        return None

    def stop(self):
        return None


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
    service = NvdaRemoteAppService(
        transport=transport,
        input_capture=FakeCapture(),
        hotkey_capture=FakeHotkey(),
        clipboard=FakeClipboard(),
        speech=FakeSpeechService(),
        main_thread_dispatch=lambda callback: callback(),
    )
    return service, transport


def test_nvda_remote_service_forwards_keys_when_controlling():
    service, transport = build_service()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.start_control()
    event = KeyEvent(vk=65, scan=30, extended=False, pressed=True)

    decision = service.handle_key_event(event)

    assert decision == KeyEventDecision.FORWARD_AND_SUPPRESS
    assert transport.sent == [(RemoteMessageType.KEY, event.to_remote_payload())]


def test_nvda_remote_service_passes_through_keys_before_control():
    service, transport = build_service()
    service.state.connection_state = service.state.connection_state.CONNECTED

    decision = service.handle_key_event(
        KeyEvent(vk=65, scan=30, extended=False, pressed=True)
    )

    assert decision == KeyEventDecision.PASS_THROUGH
    assert transport.sent == []


def test_nvda_remote_service_uses_f11_as_local_stop():
    service, transport = build_service()
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


def test_nvda_remote_service_routes_remote_speech_commands_into_speech_facade():
    service, transport = build_service()

    transport.message_handler({"type": RemoteMessageType.SPEAK.value, "sequence": ["hi"]})
    transport.message_handler({"type": RemoteMessageType.CANCEL.value})
    transport.message_handler({"type": RemoteMessageType.PAUSE_SPEECH.value, "switch": True})

    assert [speech.items for speech in service.speech.spoken] == [("hi",)]
    assert service.speech.cancelled == 1
    assert service.speech.paused == [True]


def test_nvda_remote_service_registers_transport_message_handler():
    service, transport = build_service()

    assert transport.message_handler is not None
    transport.message_handler({"type": RemoteMessageType.CHANNEL_JOINED.value})

    assert service.state.connection_state == service.state.connection_state.CONNECTED
