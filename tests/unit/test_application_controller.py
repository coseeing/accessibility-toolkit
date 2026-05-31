import pytest

from adapters.outputs.tone import LoggingToneOutput
from adapters.windows.keyboard_hook import WindowsKeyboardCapture
from remote_core.models.keys import KeyEvent
from remote_core.protocol import RemoteMessageType

from application.controller import ClientController


class FakeTransport:
    def __init__(self):
        self.sent = []
        self.connected_to = None

    def connect(self, hostname, port, insecure=False):
        self.connected_to = (hostname, port, insecure)

    def close(self):
        return None

    def send(self, message_type, **payload):
        self.sent.append((message_type, payload))


class FakeCapture:
    def __init__(self):
        self.listener = None
        self.started = 0
        self.stopped = 0

    def set_listener(self, listener):
        self.listener = listener

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1


class FakeClipboard:
    def __init__(self):
        self.text = "clip"

    def set_text(self, text):
        self.text = text

    def get_text(self):
        return self.text


def build_controller():
    transport = FakeTransport()
    capture = FakeCapture()
    clipboard = FakeClipboard()
    controller = ClientController.build_for_tests(
        transport=transport,
        input_capture=capture,
        clipboard=clipboard,
    )
    return controller, transport, capture, clipboard


def test_controller_forwards_keys_and_pushes_clipboard():
    controller, transport, capture, _clipboard = build_controller()

    controller.connect("example.com", 6837, "secret")
    controller.start_control()
    capture.listener(KeyEvent(vk=65, scan=30, extended=False, pressed=True))
    controller.push_clipboard()

    assert transport.sent[-2][0] == RemoteMessageType.KEY
    assert transport.sent[-2][1]["vk_code"] == 65
    assert transport.sent[-2][1]["scan_code"] == 30
    assert transport.sent[-1] == (
        RemoteMessageType.SET_CLIPBOARD_TEXT,
        {"text": "clip"},
    )
    assert controller.state.control_state == "controlling"


def test_key_events_are_ignored_before_controlling():
    controller, transport, capture, _clipboard = build_controller()
    controller.connect("example.com", 6837, "secret")

    capture.listener(KeyEvent(vk=65, scan=30, extended=False, pressed=True))

    assert [message_type for message_type, _payload in transport.sent] == [
        RemoteMessageType.PROTOCOL_VERSION,
        RemoteMessageType.JOIN,
    ]
    assert controller.state.control_state == "idle"


def test_stop_control_suspends_capture_and_stops_forwarding():
    controller, transport, capture, _clipboard = build_controller()
    controller.connect("example.com", 6837, "secret")
    controller.start_control()
    controller.stop_control()

    capture.listener(KeyEvent(vk=65, scan=30, extended=False, pressed=True))

    assert capture.started == 1
    assert capture.stopped == 1
    assert [message_type for message_type, _payload in transport.sent] == [
        RemoteMessageType.PROTOCOL_VERSION,
        RemoteMessageType.JOIN,
    ]
    assert controller.state.control_state == "suspended"


def test_router_clipboard_message_updates_clipboard():
    controller, _transport, _capture, clipboard = build_controller()

    controller.router.handle_message(
        {"type": RemoteMessageType.SET_CLIPBOARD_TEXT.value, "text": "remote clip"}
    )

    assert clipboard.text == "remote clip"


def test_connection_status_keeps_runtime_state_consistent():
    controller, _transport, _capture, _clipboard = build_controller()

    controller._on_status({"kind": "connection", "state": "connected"})
    assert controller.state.connection_state == "connected"
    assert controller.state.control_state == "connected"

    controller.start_control()
    controller._on_status({"kind": "connection", "state": "idle"})
    assert controller.state.connection_state == "idle"
    assert controller.state.control_state == "idle"


def test_logging_tone_output_exposes_beep_interface():
    assert LoggingToneOutput().beep(440, 100, left=40, right=60) is None


def test_windows_keyboard_capture_emits_normalized_events():
    seen = []
    capture = WindowsKeyboardCapture()
    capture.set_listener(seen.append)
    capture._emit_for_tests(vk=9, scan=15, extended=False, pressed=True)
    assert seen == [KeyEvent(vk=9, scan=15, extended=False, pressed=True)]


def test_windows_keyboard_capture_emit_without_listener_does_not_crash():
    capture = WindowsKeyboardCapture()

    capture._emit_for_tests(vk=9, scan=15, extended=False, pressed=True)


def test_windows_keyboard_capture_start_requires_windows_without_backend():
    capture = WindowsKeyboardCapture(is_windows=False)

    assert capture.running is False
    with pytest.raises(RuntimeError, match="Windows keyboard hooks require Windows"):
        capture.start()
    assert capture.running is False
