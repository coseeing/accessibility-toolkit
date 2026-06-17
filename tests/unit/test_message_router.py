from interop.protocol.connection_info import ConnectionInfo
from interop.speech.speech_commands import BreakCommand
from interop.speech.speech_sequence import SpeechSequence
from interop.protocol.messages import RemoteMessageType
from interop.protocol.routing.message_router import MessageRouter
from interop.protocol.session.remote_session import RemoteSession
from application.services import OutputManager


class DummyTransport:
    def __init__(self):
        self.sent = []
        self.connected_to = None
        self.closed = False

    def connect(self, hostname, port, insecure=False):
        self.connected_to = (hostname, port, insecure)

    def send(self, message_type, **payload):
        self.sent.append((message_type, payload))

    def close(self):
        self.closed = True


class FakeClipboard:
    def __init__(self):
        self.text = ""

    def set_text(self, text: str) -> None:
        self.text = text

    def get_text(self) -> str:
        return self.text


def build_router(seen):
    return MessageRouter(
        on_speech=lambda speech: seen.append(("speech", speech)),
        on_cancel=lambda: seen.append(("cancel", None)),
        on_pause=lambda paused: seen.append(("pause", paused)),
        on_clipboard=lambda text: seen.append(("clipboard", text)),
        on_tone=lambda hz, length, left, right: seen.append(
            ("tone", hz, length, left, right)
        ),
        on_status=lambda event: seen.append(("status", event)),
    )


def test_router_dispatches_speech_and_clipboard():
    seen = []
    router = build_router(seen)

    router.handle_message(
        {
            "type": "speak",
            "sequence": ["hello", ["BreakCommand", {"time": 50}], "world"],
        }
    )
    router.handle_message({"type": "set_clipboard_text", "text": "abc"})

    assert seen[0] == (
        "speech",
        SpeechSequence(items=("hello", BreakCommand(time=50), "world")),
    )
    assert seen[1] == ("clipboard", "abc")


def test_sequence_routes_from_router_to_backend_through_output_manager():
    seen = []

    class FakeBackend:
        def speak(self, sequence):
            seen.append(sequence)

        def cancel(self):
            return None

        def pause(self, is_paused):
            return None

        def list_voices(self):
            return ()

        def get_voice(self):
            return None

        def set_voice(self, voice_id):
            return None

        def get_rate(self):
            return None

        def set_rate(self, value):
            return None

        def get_pitch(self):
            return None

        def set_pitch(self, value):
            return None

        def get_volume(self):
            return None

        def set_volume(self, value):
            return None

    router = MessageRouter(
        on_speech=lambda sequence: OutputManager(
            FakeBackend(), FakeClipboard()
        ).handle_speech(sequence),
        on_cancel=lambda: None,
        on_pause=lambda paused: None,
        on_clipboard=lambda text: None,
        on_tone=lambda hz, length, left, right: None,
        on_status=lambda event: None,
    )

    router.handle_message(
        {
            "type": "speak",
            "sequence": ["hello", ["BreakCommand", {"time": 10}], "world"],
        }
    )

    assert seen == [
        SpeechSequence(items=("hello", BreakCommand(time=10), "world"))
    ]


def test_router_preserves_already_restored_speech_commands():
    seen = []
    router = build_router(seen)

    router.handle_message(
        {
            "type": "speak",
            "sequence": ["hello", BreakCommand(time=50), "world"],
        }
    )

    assert seen == [
        (
            "speech",
            SpeechSequence(items=("hello", BreakCommand(time=50), "world")),
        )
    ]


def test_router_dispatches_unknown_messages_to_status():
    seen = []
    router = build_router(seen)
    payload = {"type": "motd", "message": "hello"}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            {"kind": "remote", "type": "motd", "payload": payload},
        )
    ]


def test_router_reports_missing_clipboard_text_as_invalid_message():
    seen = []
    router = build_router(seen)
    payload = {"type": "set_clipboard_text"}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            {
                "kind": "invalid_message",
                "reason": "clipboard_text_must_be_string",
                "payload": payload,
            },
        )
    ]


def test_router_reports_none_clipboard_text_as_invalid_message():
    seen = []
    router = build_router(seen)
    payload = {"type": "set_clipboard_text", "text": None}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            {
                "kind": "invalid_message",
                "reason": "clipboard_text_must_be_string",
                "payload": payload,
            },
        )
    ]


def test_router_reports_non_string_clipboard_text_as_invalid_message():
    seen = []
    router = build_router(seen)
    payload = {"type": "set_clipboard_text", "text": 123}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            {
                "kind": "invalid_message",
                "reason": "clipboard_text_must_be_string",
                "payload": payload,
            },
        )
    ]


def test_session_join_sends_protocol_and_join_messages():
    transport = DummyTransport()
    status_events = []
    session = RemoteSession(
        transport=transport,
        on_status=status_events.append,
    )

    session.connect(ConnectionInfo(hostname="example.com", port=6837, key="secret"))

    assert transport.connected_to == ("example.com", 6837, False)
    assert transport.sent[0] == (RemoteMessageType.PROTOCOL_VERSION, {"version": 2})
    assert transport.sent[1][0] == RemoteMessageType.JOIN
    assert transport.sent[1][1] == {"channel": "secret", "mode": "master"}
    assert status_events == []


def test_router_dispatches_cancel_and_pause_messages():
    seen = []
    router = build_router(seen)

    router.handle_message({"type": "cancel"})
    router.handle_message({"type": "pause_speech", "switch": True})

    assert seen == [
        ("cancel", None),
        ("pause", True),
    ]


def test_router_reports_invalid_pause_payload():
    seen = []
    router = build_router(seen)
    payload = {"type": "pause_speech", "switch": "yes"}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            {
                "kind": "invalid_message",
                "reason": "pause_switch_must_be_bool",
                "payload": payload,
            },
        )
    ]


def test_session_reports_connected_after_channel_joined():
    transport = DummyTransport()
    status_events = []
    session = RemoteSession(
        transport=transport,
        on_status=status_events.append,
    )

    assert session.handle_message({"type": "channel_joined"}) is True

    assert status_events == [{"kind": "connection", "state": "connected"}]


def test_session_reports_connection_and_remote_status_messages():
    transport = DummyTransport()
    status_events = []
    session = RemoteSession(
        transport=transport,
        on_status=status_events.append,
    )
    motd = {"type": "motd", "message": "hello"}
    client_joined = {"type": "client_joined", "id": "abc"}
    client_left = {"type": "client_left", "id": "abc"}
    error = {"type": "error", "message": "bad"}

    assert session.handle_message({"type": "version_mismatch"}) is True
    assert session.handle_message(motd) is True
    assert session.handle_message(client_joined) is True
    assert session.handle_message(client_left) is True
    assert session.handle_message(error) is True
    assert session.handle_message({"type": "ping"}) is True

    assert status_events == [
        {"kind": "connection", "state": "version_mismatch"},
        {"kind": "remote", "type": "motd", "payload": motd},
        {"kind": "remote", "type": "client_joined", "payload": client_joined},
        {"kind": "remote", "type": "client_left", "payload": client_left},
        {"kind": "remote", "type": "error", "payload": error},
    ]


def test_session_does_not_handle_output_messages():
    transport = DummyTransport()
    status_events = []
    session = RemoteSession(
        transport=transport,
        on_status=status_events.append,
    )

    assert session.handle_message({"type": "speak", "sequence": ["hello"]}) is False

    assert status_events == []


def test_session_disconnect_closes_transport_and_sets_idle_status():
    transport = DummyTransport()
    status_events = []
    session = RemoteSession(
        transport=transport,
        on_status=status_events.append,
    )

    session.disconnect()

    assert transport.closed is True
    assert status_events == [{"kind": "connection", "state": "idle"}]


def test_remote_message_type_includes_nvda_remote_tone_value() -> None:
    assert RemoteMessageType.TONE.value == "tone"


def test_router_dispatches_tone_message() -> None:
    seen = []
    router = build_router(seen)

    router.handle_message(
        {
            "type": "tone",
            "hz": 440,
            "length": 80,
            "left": 25,
            "right": 75,
        }
    )

    assert seen == [("tone", 440.0, 80, 25, 75)]


def test_router_clamps_tone_balance_and_non_negative_duration() -> None:
    seen = []
    router = build_router(seen)

    router.handle_message(
        {
            "type": "tone",
            "hz": -10,
            "length": -5,
            "left": -20,
            "right": 250,
        }
    )

    assert seen == [("tone", 0.0, 0, 0, 100)]


def test_router_reports_missing_tone_field_as_invalid_message() -> None:
    seen = []
    router = build_router(seen)
    payload = {"type": "tone", "hz": 440, "length": 80, "left": 50}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            {
                "kind": "invalid_message",
                "reason": "tone_fields_must_be_numeric",
                "payload": payload,
            },
        )
    ]


def test_router_reports_non_numeric_tone_field_as_invalid_message() -> None:
    seen = []
    router = build_router(seen)
    payload = {
        "type": "tone",
        "hz": "high",
        "length": 80,
        "left": 50,
        "right": 50,
    }

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            {
                "kind": "invalid_message",
                "reason": "tone_fields_must_be_numeric",
                "payload": payload,
            },
        )
    ]
