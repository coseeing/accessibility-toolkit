import pytest

from adapters.inputs.base import KeyEventDecision
from adapters.outputs.speech import NullSpeechOutput
from adapters.outputs.tone import LoggingToneOutput
from adapters.windows.keyboard_hook import WindowsKeyboardCapture
from application.speech_backends import SpeechBackendManager, SpeechBackendOption
from remote_core.models.keys import KeyEvent
from remote_core.protocol import RemoteMessageType

from application.controller import ClientController


class FakeTransport:
    def __init__(self):
        self.sent = []
        self.connected_to = None
        self.message_handler = None
        self.reader_started = 0
        self.reader_stopped = 0

    def connect(self, hostname, port, insecure=False):
        self.connected_to = (hostname, port, insecure)

    def close(self):
        return None

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
        self.listener = None
        self.started = 0
        self.stopped = 0
        self.running = False

    def set_listener(self, listener):
        self.listener = listener

    def start(self):
        self.started += 1
        self.running = True

    def stop(self):
        self.stopped += 1
        self.running = False


class FakeClipboard:
    def __init__(self):
        self.text = "clip"

    def set_text(self, text):
        self.text = text

    def get_text(self):
        return self.text


class FakeHotkeyCapture:
    def __init__(self):
        self.handler = None
        self.started = 0
        self.stopped = 0
        self.running = False

    def set_handler(self, handler):
        self.handler = handler

    def start(self):
        self.started += 1
        self.running = True

    def stop(self):
        self.stopped += 1
        self.running = False


class FakeSpeechOutput:
    def __init__(self, name: str, events: list[tuple[str, str]]):
        self.name = name
        self.events = events
        self.voice_id = "voice-0"
        self.rate = 100
        self.pitch = 0
        self.volume = 100
        self.voices = (("voice-0", "Voice 0"), ("voice-1", "Voice 1"))

    def speak(self, speech) -> None:
        self.events.append(("speak", self.name))

    def cancel(self) -> None:
        self.events.append(("cancel", self.name))

    def pause(self, is_paused: bool) -> None:
        self.events.append(("pause", self.name))

    def list_voices(self):
        return self.voices

    def get_voice(self):
        return self.voice_id

    def set_voice(self, voice_id: str) -> None:
        self.voice_id = voice_id

    def get_rate(self):
        return self.rate

    def set_rate(self, value: int) -> None:
        self.rate = value

    def get_pitch(self):
        return self.pitch

    def set_pitch(self, value: int) -> None:
        self.pitch = value

    def get_volume(self):
        return self.volume

    def set_volume(self, value: int) -> None:
        self.volume = value


def build_controller(speech_backend_manager=None, main_thread_dispatch=None):
    transport = FakeTransport()
    capture = FakeCapture()
    clipboard = FakeClipboard()
    hotkey = FakeHotkeyCapture()
    controller = ClientController.build_for_tests(
        transport=transport,
        input_capture=capture,
        clipboard=clipboard,
        hotkey_capture=hotkey,
        speech_backend_manager=speech_backend_manager,
        main_thread_dispatch=main_thread_dispatch,
    )
    return controller, transport, capture, clipboard, hotkey


def test_controller_forwards_keys_and_pushes_clipboard():
    controller, transport, capture, _clipboard, hotkey = build_controller()

    controller.connect("example.com", 6837, "secret")
    transport.message_handler({"type": RemoteMessageType.CHANNEL_JOINED.value})
    controller.start_control()
    decision = capture.listener(KeyEvent(vk=65, scan=30, extended=False, pressed=True))
    controller.push_clipboard()

    assert transport.sent[-2][0] == RemoteMessageType.KEY
    assert transport.sent[-2][1]["vk_code"] == 65
    assert transport.sent[-2][1]["scan_code"] == 30
    assert decision == KeyEventDecision.FORWARD_AND_SUPPRESS
    assert transport.sent[-1] == (
        RemoteMessageType.SET_CLIPBOARD_TEXT,
        {"text": "clip"},
    )
    assert controller.state.control_state == "controlling"
    assert hotkey.started == 1
    assert hotkey.stopped == 1


def test_key_events_are_ignored_before_controlling():
    controller, transport, capture, _clipboard, _hotkey = build_controller()
    controller.connect("example.com", 6837, "secret")

    decision = capture.listener(KeyEvent(vk=65, scan=30, extended=False, pressed=True))

    assert [message_type for message_type, _payload in transport.sent] == [
        RemoteMessageType.PROTOCOL_VERSION,
        RemoteMessageType.JOIN,
    ]
    assert decision == KeyEventDecision.PASS_THROUGH
    assert controller.state.control_state == "idle"


def test_stop_control_suspends_capture_and_stops_forwarding():
    controller, transport, capture, _clipboard, hotkey = build_controller()
    controller.connect("example.com", 6837, "secret")
    transport.message_handler({"type": RemoteMessageType.CHANNEL_JOINED.value})
    controller.start_control()
    controller.stop_control()

    decision = capture.listener(KeyEvent(vk=65, scan=30, extended=False, pressed=True))

    assert capture.started == 1
    assert capture.stopped == 1
    assert hotkey.started == 2
    assert hotkey.stopped == 1
    assert [message_type for message_type, _payload in transport.sent] == [
        RemoteMessageType.PROTOCOL_VERSION,
        RemoteMessageType.JOIN,
    ]
    assert decision == KeyEventDecision.PASS_THROUGH
    assert controller.state.control_state == "suspended"


def test_f11_stops_control_locally_without_forwarding():
    controller, transport, capture, _clipboard, hotkey = build_controller()
    statuses = []
    controller.set_status_listener(statuses.append)
    controller.connect("example.com", 6837, "secret")
    transport.message_handler({"type": RemoteMessageType.CHANNEL_JOINED.value})
    controller.start_control()

    keydown_decision = capture.listener(
        KeyEvent(vk=0x7A, scan=87, extended=False, pressed=True)
    )
    keyup_decision = capture.listener(
        KeyEvent(vk=0x7A, scan=87, extended=False, pressed=False)
    )

    assert keydown_decision == KeyEventDecision.LOCAL_ONLY_SUPPRESS
    assert keyup_decision == KeyEventDecision.LOCAL_ONLY_SUPPRESS
    assert capture.stopped == 1
    assert hotkey.started == 2
    assert hotkey.stopped == 1
    assert controller.state.connection_state == "connected"
    assert controller.state.control_state == "suspended"
    assert [message_type for message_type, _payload in transport.sent] == [
        RemoteMessageType.PROTOCOL_VERSION,
        RemoteMessageType.JOIN,
    ]
    assert statuses[-1]["kind"] == "control"
    assert statuses[-1]["state"] == "suspended"


def test_f11_hotkey_starts_control_when_connected_but_not_controlling():
    controller, transport, capture, _clipboard, hotkey = build_controller()
    statuses = []
    controller.set_status_listener(statuses.append)
    controller.connect("example.com", 6837, "secret")
    transport.message_handler({"type": RemoteMessageType.CHANNEL_JOINED.value})

    hotkey.handler()

    assert capture.started == 1
    assert capture.stopped == 0
    assert hotkey.started == 1
    assert hotkey.stopped == 1
    assert controller.state.connection_state == "connected"
    assert controller.state.control_state == "controlling"
    assert [message_type for message_type, _payload in transport.sent] == [
        RemoteMessageType.PROTOCOL_VERSION,
        RemoteMessageType.JOIN,
    ]
    assert statuses[-1]["kind"] == "control"
    assert statuses[-1]["state"] == "controlling"


def test_f11_hotkey_can_dispatch_control_start_to_main_thread():
    scheduled = []
    controller, transport, capture, _clipboard, hotkey = build_controller(
        main_thread_dispatch=scheduled.append
    )
    controller.connect("example.com", 6837, "secret")
    transport.message_handler({"type": RemoteMessageType.CHANNEL_JOINED.value})

    hotkey.handler()

    assert len(scheduled) == 1
    assert capture.started == 0
    assert controller.state.control_state == "connected"

    scheduled[0]()

    assert capture.started == 1
    assert hotkey.stopped == 1
    assert controller.state.control_state == "controlling"


def test_f11_hotkey_does_nothing_when_not_connected():
    controller, transport, capture, _clipboard, hotkey = build_controller()

    hotkey.handler()

    assert capture.started == 0
    assert capture.stopped == 0
    assert hotkey.started == 0
    assert hotkey.stopped == 0
    assert controller.state.connection_state == "idle"
    assert controller.state.control_state == "idle"
    assert transport.sent == []


def test_router_clipboard_message_updates_clipboard():
    controller, _transport, _capture, clipboard, _hotkey = build_controller()

    controller.router.handle_message(
        {"type": RemoteMessageType.SET_CLIPBOARD_TEXT.value, "text": "remote clip"}
    )

    assert clipboard.text == "remote clip"


def test_connection_status_keeps_runtime_state_consistent():
    controller, _transport, _capture, _clipboard, _hotkey = build_controller()

    controller._on_status({"kind": "connection", "state": "connected"})
    assert controller.state.connection_state == "connected"
    assert controller.state.control_state == "connected"

    controller.start_control()
    controller._on_status({"kind": "connection", "state": "idle"})
    assert controller.state.connection_state == "idle"
    assert controller.state.control_state == "idle"


def test_controller_starts_reader_and_consumes_inbound_channel_joined():
    controller, transport, capture, _clipboard, hotkey = build_controller()

    controller.connect("example.com", 6837, "secret")
    transport.message_handler({"type": RemoteMessageType.CHANNEL_JOINED.value})

    assert transport.reader_started == 1
    assert capture.started == 0
    assert hotkey.started == 1
    assert controller.state.connection_state == "connected"
    assert controller.state.control_state == "connected"


def test_controller_disconnect_stops_reader_and_sets_idle():
    controller, transport, capture, _clipboard, hotkey = build_controller()
    controller.connect("example.com", 6837, "secret")
    transport.message_handler({"type": RemoteMessageType.CHANNEL_JOINED.value})
    controller.disconnect()

    assert transport.reader_stopped == 1
    assert capture.stopped == 0
    assert hotkey.stopped == 1
    assert controller.state.connection_state == "idle"
    assert controller.state.control_state == "idle"


def test_controller_disconnect_stops_control_before_session_disconnect():
    controller, transport, capture, _clipboard, hotkey = build_controller()

    controller.connect("example.com", 6837, "secret")
    transport.message_handler({"type": RemoteMessageType.CHANNEL_JOINED.value})
    controller.start_control()
    controller.disconnect()

    assert capture.started == 1
    assert capture.stopped == 1
    assert hotkey.started == 2
    assert hotkey.stopped == 2
    assert transport.reader_stopped == 1
    assert controller.state.connection_state == "idle"
    assert controller.state.control_state == "idle"


def test_controller_switches_speech_backend_and_notifies_ui():
    events: list[tuple[str, str]] = []
    backend_manager = SpeechBackendManager(
        backend_options=(
            SpeechBackendOption(
                backend_id="nvda_controller",
                label="NVDA Controller",
                factory=lambda: FakeSpeechOutput("nvda_controller", events),
            ),
            SpeechBackendOption(
                backend_id="pyttsx3",
                label="pyttsx3",
                factory=lambda: FakeSpeechOutput("pyttsx3", events),
            ),
        ),
        selected_backend_id="nvda_controller",
    )
    controller, _transport, _capture, _clipboard, _hotkey = build_controller(
        speech_backend_manager=backend_manager
    )
    statuses = []
    controller.set_status_listener(statuses.append)

    controller.set_speech_backend("pyttsx3")

    assert controller.get_selected_speech_backend() == "pyttsx3"
    assert controller.get_speech_backend_options() == (
        ("nvda_controller", "NVDA Controller"),
        ("pyttsx3", "pyttsx3"),
    )
    assert events == [("cancel", "nvda_controller")]
    assert statuses[-1] == {"kind": "speech_backend", "backend_id": "pyttsx3"}


def test_controller_exposes_voice_and_prosody_controls():
    backend_manager = SpeechBackendManager(
        backend_options=(
            SpeechBackendOption(
                backend_id="pyttsx3",
                label="pyttsx3",
                factory=lambda: FakeSpeechOutput("pyttsx3", []),
            ),
        ),
        selected_backend_id="pyttsx3",
    )
    controller, _transport, _capture, _clipboard, _hotkey = build_controller(
        speech_backend_manager=backend_manager
    )

    assert controller.get_available_voices()

    controller.set_selected_voice("voice-1")
    controller.set_rate(120)
    controller.set_pitch(3)
    controller.set_volume(80)

    assert controller.get_selected_voice() == "voice-1"
    assert controller.get_rate() == 120
    assert controller.get_pitch() == 3
    assert controller.get_volume() == 80


def test_controller_starts_f11_hotkey_when_session_connects():
    controller, transport, capture, _clipboard, hotkey = build_controller()

    controller.connect("example.com", 6837, "secret")
    transport.message_handler({"type": RemoteMessageType.CHANNEL_JOINED.value})

    assert capture.started == 0
    assert capture.stopped == 0
    assert hotkey.started == 1
    assert hotkey.stopped == 0
    assert controller.state.connection_state == "connected"
    assert controller.state.control_state == "connected"


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
